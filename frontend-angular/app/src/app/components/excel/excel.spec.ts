import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Excel } from './excel';

describe('Excel', () => {
  let component: Excel;
  let fixture: ComponentFixture<Excel>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Excel],
    }).compileComponents();

    fixture = TestBed.createComponent(Excel);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
