import { TestBed } from '@angular/core/testing';

import { fichahospitalaria } from './ficha-hospitalaria';

describe('FichaHospitalaria', () => {
  let service: fichahospitalaria;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(fichahospitalaria);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
