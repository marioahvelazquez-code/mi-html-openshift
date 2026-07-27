import { Routes, UrlMatcher, UrlSegment } from '@angular/router';

const loginSignalMatcher: UrlMatcher = (segments: UrlSegment[]) => {
  if (segments.length !== 1) {
    return null;
  }

  const match = segments[0].path.match(/^login&x=([01])$/);
  if (!match) {
    return null;
  }

  return {
    consumed: segments,
    posParams: {
      x: new UrlSegment(match[1], {}),
    },
  };
};

export const routes: Routes = [
  {
    matcher: loginSignalMatcher,
    loadComponent: () => import('./components/login/login').then((m) => m.LoginComponent),
  },
  {
    path: 'login',
    loadComponent: () => import('./components/login/login').then((m) => m.LoginComponent),
  },
  {
    path: '',
    redirectTo: 'login',
    pathMatch: 'full',
  },
  {
    path: '**',
    redirectTo: 'login',
  },
];
