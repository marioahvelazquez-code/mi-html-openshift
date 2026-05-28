import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CarruselHome } from './carrusel-home';

describe('CarruselHome', () => {
  let component: CarruselHome;
  let fixture: ComponentFixture<CarruselHome>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CarruselHome],
    }).compileComponents();

    fixture = TestBed.createComponent(CarruselHome);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
