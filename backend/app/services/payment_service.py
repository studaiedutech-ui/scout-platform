"""
Payment Service for SaaS Platform
Handles Stripe payment integration for subscriptions
"""

import stripe
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus, BillingInterval
from app.models.company import Company
from app.models.user import User

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


class StripePaymentService:
    """
    Stripe payment service for subscription management
    """
    
    def __init__(self):
        self.webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    
    def create_customer(self, company: Company, user: User) -> Optional[str]:
        """
        Create a Stripe customer for the company
        """
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=company.name,
                description=f"Company: {company.name} (ID: {company.id})",
                metadata={
                    'company_id': str(company.id),
                    'user_id': str(user.id),
                    'environment': settings.ENVIRONMENT
                }
            )
            
            logger.info(f"Created Stripe customer {customer.id} for company {company.id}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer for company {company.id}: {str(e)}")
            return None
    
    def create_subscription(self, db: Session, company_id: int, plan_id: int, 
                           billing_interval: BillingInterval, stripe_customer_id: str,
                           payment_method_id: str) -> Optional[Dict[str, Any]]:
        """
        Create a Stripe subscription
        """
        try:
            # Get the subscription plan
            plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
            if not plan:
                raise ValueError("Subscription plan not found")
            
            # Determine price based on billing interval
            price_amount = int(plan.get_price(billing_interval) * 100)  # Convert to cents
            
            # Create a price object
            price = stripe.Price.create(
                unit_amount=price_amount,
                currency=plan.currency.lower(),
                recurring={
                    'interval': 'month' if billing_interval == BillingInterval.MONTHLY else 'year'
                },
                product_data={
                    'name': f"{plan.name} Plan",
                    'description': plan.description
                },
                metadata={
                    'plan_id': str(plan.id),
                    'plan_type': plan.plan_type.value
                }
            )
            
            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=stripe_customer_id
            )
            
            # Set as default payment method
            stripe.Customer.modify(
                stripe_customer_id,
                invoice_settings={
                    'default_payment_method': payment_method_id
                }
            )
            
            # Create subscription
            stripe_subscription = stripe.Subscription.create(
                customer=stripe_customer_id,
                items=[{'price': price.id}],
                trial_period_days=plan.trial_days if plan.trial_days > 0 else None,
                expand=['latest_invoice.payment_intent'],
                metadata={
                    'company_id': str(company_id),
                    'plan_id': str(plan_id),
                    'environment': settings.ENVIRONMENT
                }
            )
            
            # Update local subscription
            subscription = db.query(Subscription).filter(
                Subscription.company_id == company_id
            ).first()
            
            if subscription:
                subscription.stripe_subscription_id = stripe_subscription.id
                subscription.stripe_customer_id = stripe_customer_id
                subscription.status = self._map_stripe_status(stripe_subscription.status)
                subscription.current_period_start = datetime.fromtimestamp(
                    stripe_subscription.current_period_start
                )
                subscription.current_period_end = datetime.fromtimestamp(
                    stripe_subscription.current_period_end
                )
                subscription.trial_start = datetime.fromtimestamp(
                    stripe_subscription.trial_start
                ) if stripe_subscription.trial_start else None
                subscription.trial_end = datetime.fromtimestamp(
                    stripe_subscription.trial_end
                ) if stripe_subscription.trial_end else None
                
                db.commit()
            
            logger.info(f"Created Stripe subscription {stripe_subscription.id} for company {company_id}")
            
            return {
                'subscription_id': stripe_subscription.id,
                'client_secret': stripe_subscription.latest_invoice.payment_intent.client_secret,
                'status': stripe_subscription.status
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe subscription for company {company_id}: {str(e)}")
            return None
    
    def cancel_subscription(self, db: Session, subscription_id: str) -> bool:
        """
        Cancel a Stripe subscription
        """
        try:
            # Cancel the subscription at period end
            stripe_subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            
            # Update local subscription
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).first()
            
            if subscription:
                subscription.status = SubscriptionStatus.CANCELLED
                subscription.cancelled_at = datetime.utcnow()
                subscription.ends_at = datetime.fromtimestamp(
                    stripe_subscription.current_period_end
                )
                db.commit()
            
            logger.info(f"Cancelled Stripe subscription {subscription_id}")
            return True
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel Stripe subscription {subscription_id}: {str(e)}")
            return False
    
    def update_subscription(self, db: Session, subscription_id: str, new_plan_id: int) -> bool:
        """
        Update a Stripe subscription to a new plan
        """
        try:
            # Get current subscription
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Get new plan
            new_plan = db.query(SubscriptionPlan).filter(
                SubscriptionPlan.id == new_plan_id
            ).first()
            if not new_plan:
                raise ValueError("New subscription plan not found")
            
            # Get current billing interval from local subscription
            local_subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).first()
            
            billing_interval = local_subscription.billing_interval if local_subscription else BillingInterval.MONTHLY
            
            # Create new price
            price_amount = int(new_plan.get_price(billing_interval) * 100)
            price = stripe.Price.create(
                unit_amount=price_amount,
                currency=new_plan.currency.lower(),
                recurring={
                    'interval': 'month' if billing_interval == BillingInterval.MONTHLY else 'year'
                },
                product_data={
                    'name': f"{new_plan.name} Plan",
                    'description': new_plan.description
                }
            )
            
            # Update subscription
            stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': stripe_subscription['items']['data'][0].id,
                    'price': price.id,
                }],
                proration_behavior='create_prorations'
            )
            
            # Update local subscription
            if local_subscription:
                local_subscription.plan_id = new_plan_id
                db.commit()
            
            logger.info(f"Updated Stripe subscription {subscription_id} to plan {new_plan_id}")
            return True
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update Stripe subscription {subscription_id}: {str(e)}")
            return False
    
    def handle_webhook(self, payload: bytes, signature: str) -> Optional[Dict[str, Any]]:
        """
        Handle Stripe webhook events
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            logger.info(f"Received Stripe webhook: {event['type']}")
            
            return {
                'event_type': event['type'],
                'event_data': event['data']['object']
            }
            
        except ValueError as e:
            logger.error(f"Invalid Stripe webhook payload: {str(e)}")
            return None
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid Stripe webhook signature: {str(e)}")
            return None
    
    def process_webhook_event(self, db: Session, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Process specific webhook events
        """
        try:
            if event_type == 'customer.subscription.updated':
                return self._handle_subscription_updated(db, event_data)
            elif event_type == 'customer.subscription.deleted':
                return self._handle_subscription_deleted(db, event_data)
            elif event_type == 'invoice.payment_succeeded':
                return self._handle_payment_succeeded(db, event_data)
            elif event_type == 'invoice.payment_failed':
                return self._handle_payment_failed(db, event_data)
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing webhook event {event_type}: {str(e)}")
            return False
    
    def _handle_subscription_updated(self, db: Session, subscription_data: Dict[str, Any]) -> bool:
        """
        Handle subscription updated webhook
        """
        subscription_id = subscription_data.get('id')
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = self._map_stripe_status(subscription_data.get('status'))
            subscription.current_period_start = datetime.fromtimestamp(
                subscription_data.get('current_period_start')
            )
            subscription.current_period_end = datetime.fromtimestamp(
                subscription_data.get('current_period_end')
            )
            
            if subscription_data.get('canceled_at'):
                subscription.cancelled_at = datetime.fromtimestamp(
                    subscription_data.get('canceled_at')
                )
            
            db.commit()
            logger.info(f"Updated local subscription {subscription.id} from webhook")
        
        return True
    
    def _handle_subscription_deleted(self, db: Session, subscription_data: Dict[str, Any]) -> bool:
        """
        Handle subscription deleted webhook
        """
        subscription_id = subscription_data.get('id')
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.ends_at = datetime.utcnow()
            db.commit()
            logger.info(f"Cancelled local subscription {subscription.id} from webhook")
        
        return True
    
    def _handle_payment_succeeded(self, db: Session, invoice_data: Dict[str, Any]) -> bool:
        """
        Handle successful payment webhook
        """
        subscription_id = invoice_data.get('subscription')
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.last_payment_at = datetime.utcnow()
            subscription.status = SubscriptionStatus.ACTIVE
            
            # Update next billing date
            if invoice_data.get('period_end'):
                subscription.next_billing_date = datetime.fromtimestamp(
                    invoice_data.get('period_end')
                )
            
            db.commit()
            logger.info(f"Updated payment info for subscription {subscription.id}")
        
        return True
    
    def _handle_payment_failed(self, db: Session, invoice_data: Dict[str, Any]) -> bool:
        """
        Handle failed payment webhook
        """
        subscription_id = invoice_data.get('subscription')
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = SubscriptionStatus.PAST_DUE
            db.commit()
            logger.info(f"Marked subscription {subscription.id} as past due")
        
        return True
    
    def _map_stripe_status(self, stripe_status: str) -> SubscriptionStatus:
        """
        Map Stripe subscription status to local status
        """
        mapping = {
            'active': SubscriptionStatus.ACTIVE,
            'trialing': SubscriptionStatus.TRIAL,
            'past_due': SubscriptionStatus.PAST_DUE,
            'canceled': SubscriptionStatus.CANCELLED,
            'unpaid': SubscriptionStatus.UNPAID
        }
        
        return mapping.get(stripe_status, SubscriptionStatus.UNPAID)
    
    def get_billing_portal_url(self, customer_id: str, return_url: str) -> Optional[str]:
        """
        Create a billing portal session for customer self-service
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url
            )
            
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create billing portal for customer {customer_id}: {str(e)}")
            return None
    
    def get_usage_records(self, subscription_id: str) -> List[Dict[str, Any]]:
        """
        Get usage records for metered billing (if needed in future)
        """
        try:
            # This would be used for usage-based billing
            # For now, return empty list as we're using flat-rate pricing
            return []
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get usage records for subscription {subscription_id}: {str(e)}")
            return []


class PaymentWebhookHandler:
    """
    Handler for processing payment webhooks
    """
    
    def __init__(self, payment_service: StripePaymentService, notification_service):
        self.payment_service = payment_service
        self.notification_service = notification_service
    
    def handle_webhook(self, db: Session, payload: bytes, signature: str) -> bool:
        """
        Handle incoming webhook
        """
        # Verify and parse webhook
        event = self.payment_service.handle_webhook(payload, signature)
        if not event:
            return False
        
        # Process the event
        success = self.payment_service.process_webhook_event(
            db, event['event_type'], event['event_data']
        )
        
        # Send notifications if needed
        if success:
            self._send_webhook_notifications(db, event['event_type'], event['event_data'])
        
        return success
    
    def _send_webhook_notifications(self, db: Session, event_type: str, event_data: Dict[str, Any]):
        """
        Send notifications based on webhook events
        """
        try:
            if event_type == 'invoice.payment_failed':
                self._notify_payment_failed(db, event_data)
            elif event_type == 'customer.subscription.trial_will_end':
                self._notify_trial_ending(db, event_data)
            # Add more notification triggers as needed
                
        except Exception as e:
            logger.error(f"Error sending webhook notifications: {str(e)}")
    
    def _notify_payment_failed(self, db: Session, invoice_data: Dict[str, Any]):
        """
        Notify about failed payment
        """
        subscription_id = invoice_data.get('subscription')
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription and subscription.company:
            # Get company admin
            admin = db.query(User).filter(
                User.company_id == subscription.company_id,
                User.role == 'company_admin'
            ).first()
            
            if admin:
                amount = invoice_data.get('amount_due', 0) / 100  # Convert from cents
                self.notification_service.send_payment_failed(
                    user_email=admin.email,
                    user_name=admin.full_name,
                    company_name=subscription.company.name,
                    plan_name=subscription.plan.name,
                    amount=amount
                )
    
    def _notify_trial_ending(self, db: Session, subscription_data: Dict[str, Any]):
        """
        Notify about trial ending
        """
        subscription_id = subscription_data.get('id')
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription and subscription.company:
            admin = db.query(User).filter(
                User.company_id == subscription.company_id,
                User.role == 'company_admin'
            ).first()
            
            if admin and subscription.trial_end:
                days_remaining = (subscription.trial_end - datetime.utcnow()).days
                self.notification_service.send_trial_ending_warning(
                    user_email=admin.email,
                    user_name=admin.full_name,
                    company_name=subscription.company.name,
                    days_remaining=max(0, days_remaining)
                )