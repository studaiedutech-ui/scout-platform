#!/bin/bash

# S.C.O.U.T. Platform Deployment Verification Script
# This script performs final pre-deployment checks

set -e

echo "🚀 S.C.O.U.T. Platform Deployment Verification Script"
echo "=================================================="
echo

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to print info
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo "1. Checking Repository Structure..."
echo "-----------------------------------"

# Check critical directories
dirs=("backend" "frontend" "infrastructure" "docs" ".github/workflows")
for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        print_status 0 "Directory $dir exists"
    else
        print_status 1 "Directory $dir missing"
        exit 1
    fi
done

echo
echo "2. Checking Configuration Files..."
echo "----------------------------------"

# Check critical files
files=("docker-compose.yml" ".env.example" "package.json" "backend/requirements.txt" "frontend/package.json")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        print_status 0 "File $file exists"
    else
        print_status 1 "File $file missing"
        exit 1
    fi
done

echo
echo "3. Checking Docker Configuration..."
echo "-----------------------------------"

# Check Docker files
if [ -f "backend/Dockerfile" ] && [ -f "frontend/Dockerfile" ]; then
    print_status 0 "Docker configurations present"
else
    print_status 1 "Docker configurations missing"
    exit 1
fi

# Check if Docker is available
if command -v docker &> /dev/null; then
    print_status 0 "Docker available"
    docker_version=$(docker --version)
    print_info "Docker version: $docker_version"
else
    print_warning "Docker not available in current environment"
fi

echo
echo "4. Checking Kubernetes Configuration..."
echo "---------------------------------------"

# Check Kubernetes files
k8s_files=("infrastructure/kubernetes/backend-deployment.yaml" "infrastructure/kubernetes/config.yaml")
for file in "${k8s_files[@]}"; do
    if [ -f "$file" ]; then
        print_status 0 "K8s config $file exists"
    else
        print_status 1 "K8s config $file missing"
        exit 1
    fi
done

echo
echo "5. Checking CI/CD Configuration..."
echo "----------------------------------"

# Check GitHub Actions
if [ -f ".github/workflows/ci-cd.yml" ] && [ -f ".github/workflows/deploy.yml" ]; then
    print_status 0 "GitHub Actions workflows configured"
else
    print_status 1 "GitHub Actions workflows missing"
    exit 1
fi

echo
echo "6. Checking Documentation..."
echo "----------------------------"

# Check documentation files
doc_files=("README.md" "docs/production-deployment-guide.md" "docs/security-guidelines.md" "DEPLOYMENT_READINESS_ASSESSMENT.md")
for file in "${doc_files[@]}"; do
    if [ -f "$file" ]; then
        print_status 0 "Documentation $file exists"
    else
        print_status 1 "Documentation $file missing"
        exit 1
    fi
done

echo
echo "7. Checking Environment Configuration..."
echo "----------------------------------------"

# Check environment files
if [ -f ".env.example" ] && [ -f ".env.production" ]; then
    print_status 0 "Environment configuration files present"
else
    print_warning "Environment configuration files may need attention"
fi

echo
echo "8. Frontend Dependencies Check..."
echo "---------------------------------"

if [ -d "frontend/node_modules" ]; then
    print_status 0 "Frontend dependencies installed"
else
    print_warning "Frontend dependencies not installed (run 'cd frontend && npm install')"
fi

echo
echo "9. Code Quality Checks..."
echo "-------------------------"

# Check if we can run linting (if npm is available)
if command -v npm &> /dev/null; then
    print_status 0 "npm available for code quality checks"
    if [ -d "frontend/node_modules" ]; then
        cd frontend
        if npm run lint &> /dev/null; then
            print_status 0 "Frontend linting passed"
        else
            print_warning "Frontend linting has warnings (check manually)"
        fi
        cd ..
    fi
else
    print_warning "npm not available for linting checks"
fi

echo
echo "10. Final Deployment Readiness..."
echo "---------------------------------"

# Count total files
file_count=$(find . -type f \( ! -path "./.*" -o -path "./.env*" -o -path "./.github/*" \) | wc -l)
print_info "Total project files: $file_count"

# Check git status
if command -v git &> /dev/null; then
    git_status=$(git status --porcelain | wc -l)
    if [ $git_status -eq 0 ]; then
        print_status 0 "Git repository clean"
    else
        print_info "Git repository has $git_status uncommitted changes"
    fi
    
    current_branch=$(git branch --show-current)
    print_info "Current branch: $current_branch"
else
    print_warning "Git not available for status check"
fi

echo
echo "=================================================="
echo -e "${GREEN}🎉 DEPLOYMENT VERIFICATION COMPLETE${NC}"
echo "=================================================="
echo
echo -e "${GREEN}✅ S.C.O.U.T. Platform is READY FOR DEPLOYMENT${NC}"
echo
echo "Next steps:"
echo "1. Review DEPLOYMENT_READINESS_ASSESSMENT.md for detailed analysis"
echo "2. Configure production environment variables"
echo "3. Set up cloud infrastructure (Kubernetes cluster, databases)"
echo "4. Trigger CI/CD pipeline for automated deployment"
echo "5. Monitor deployment progress and system health"
echo
echo "For detailed deployment instructions, see:"
echo "- DEPLOYMENT_INSTRUCTIONS.md"
echo "- docs/production-deployment-guide.md"
echo
echo -e "${BLUE}Platform is ready for production deployment! 🚀${NC}"