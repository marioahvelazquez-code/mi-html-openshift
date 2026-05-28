import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BitacoraComponent } from './bitacora';

describe('BitacoraComponent', () => {
  let component: BitacoraComponent;
  let fixture: ComponentFixture<BitacoraComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BitacoraComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(BitacoraComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
