import { configureStore } from '@reduxjs/toolkit';
import authSlice from './authSlice';
import companySlice from './companySlice';
import assessmentSlice from './assessmentSlice';
import notificationSlice from './notificationSlice';

export const store = configureStore({
  reducer: {
    auth: authSlice,
    company: companySlice,
    assessment: assessmentSlice,
    notifications: notificationSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;