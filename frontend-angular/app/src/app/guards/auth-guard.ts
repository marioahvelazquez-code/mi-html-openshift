import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';

import { AuthService } from '../services/auth';

export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isLoggedIn()) {
    const isRestricted = auth.hasRestrictedSolicitudAccess();
    if (
      isRestricted &&
      state.url !== '/solicitud-acceso-bd' &&
      state.url !== '/solicitudes-realizadas'
    ) {
      router.navigate(['/solicitud-acceso-bd']);
      return false;
    }
    return true;
  }

  router.navigate(['/login']);
  return false;
};
