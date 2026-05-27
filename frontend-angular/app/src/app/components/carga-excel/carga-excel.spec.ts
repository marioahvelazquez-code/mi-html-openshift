import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CargaExcelComponent } from './carga-excel';

describe('CargaExcelComponent', () => {
  let component: CargaExcelComponent;
  let fixture: ComponentFixture<CargaExcelComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CargaExcelComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(CargaExcelComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
