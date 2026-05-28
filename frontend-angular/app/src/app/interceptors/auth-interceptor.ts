import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

import { AuthService } from '../services/auth';

import { Router } from '@angular/router';
import { catchError } from 'rxjs/operators';
import { throwError } from 'rxjs';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  console.log('INTERCEPTOR FUNCIONANDO');
  console.log(req.url);

  const auth = inject(AuthService);
  const router = inject(Router);

  // const token = localStorage.getItem('token');
  const token = sessionStorage.getItem('token');

  console.log('TOKEN:', token);

  if (token) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  auth.updateActivity();

  return next(req).pipe(
    catchError((err) => {
      if (err.status === 401) {
        auth.logout();
      }
      return throwError(() => err);
    }),
  );
};
