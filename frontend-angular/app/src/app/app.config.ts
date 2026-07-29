import { ApplicationConfig, importProvidersFrom } from '@angular/core';

import { provideHttpClient, withInterceptors } from '@angular/common/http';

import { provideRouter } from '@angular/router';

import { routes } from './app.routes';

import { authInterceptor } from './interceptors/auth-interceptor';

import {
  LucideAngularModule,
  Menu,
  MessageCircleMore,
  X,
  Home,
  Columns4,
  BetweenHorizontalStart,
  PanelsTopLeft,
  LayoutDashboard,
  DatabaseSearch,
  LogOut,
  ChartColumn,
  FileText,
  Hospital,
  MapPin,
  Building2,
  ShieldCheck,
  Hash,
  MessageSquare,
  Send,
  ChevronDown,
} from 'lucide-angular';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),

    provideHttpClient(withInterceptors([authInterceptor])),

    importProvidersFrom(
      LucideAngularModule.pick({
        Menu,
        MessageCircleMore,
        X,
        Home,
        Columns4,
        BetweenHorizontalStart,
        PanelsTopLeft,
        LayoutDashboard,
        DatabaseSearch,
        LogOut,
        ChartColumn,
        FileText,
        Hospital,
        MapPin,
        Building2,
        ShieldCheck,
        Hash,
        MessageSquare,
        Send,
        ChevronDown,
      }),
    ),
  ],
};
