import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FichaHospitalaria } from './ficha-hospitalaria';

describe('FichaHospitalaria', () => {
  let component: FichaHospitalaria;
  let fixture: ComponentFixture<FichaHospitalaria>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FichaHospitalaria],
    }).compileComponents();

    fixture = TestBed.createComponent(FichaHospitalaria);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
