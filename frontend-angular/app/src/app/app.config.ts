import { ApplicationConfig, importProvidersFrom } from '@angular/core';

import { provideHttpClient, withInterceptors } from '@angular/common/http';

import { provideRouter } from '@angular/router';

import { routes } from './app.routes';

import { authInterceptor } from './interceptors/auth-interceptor';

import {
  LucideAngularModule,
  Menu,
  X,
  Home,
  Columns4,
  BetweenHorizontalStart,
  PanelsTopLeft,
  LayoutDashboard,
  MessageSquare,
  Send,
  DatabaseSearch,
  LogOut,
} from 'lucide-angular';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),

    provideHttpClient(withInterceptors([authInterceptor])),

    importProvidersFrom(
      LucideAngularModule.pick({
        Menu,
        X,
        Home,
        Columns4,
        BetweenHorizontalStart,
        PanelsTopLeft,
        LayoutDashboard,
        MessageSquare,
        Send,
        DatabaseSearch,
        LogOut,
      }),
    ),
  ],
};
