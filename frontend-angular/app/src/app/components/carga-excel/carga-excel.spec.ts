import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Observable, Subject, of } from 'rxjs';

import { CargaExcelComponent } from './carga-excel';
import { CargaExcelService } from './carga-excel.service';

describe('CargaExcelComponent', () => {
  let component: CargaExcelComponent;
  let fixture: ComponentFixture<CargaExcelComponent>;
  let hojasPendientes: Subject<any>[];
  let cargasPendientes: Subject<any>[];
  let archivosConsultados: File[];
  let cargasSolicitadas: any[];
  let service: {
    getAreas: () => Observable<any[]>;
    getTemas: (idArea: number) => Observable<any[]>;
    getDiccionario: (idTema: number) => Observable<any[]>;
    obtenerHojas: (archivo: File) => Observable<any>;
    subirExcel: (
      idArea: number,
      idTema: number,
      archivo: File,
      hoja: string,
    ) => Observable<any>;
  };

  beforeEach(async () => {
    hojasPendientes = [];
    cargasPendientes = [];
    archivosConsultados = [];
    cargasSolicitadas = [];
    service = {
      getAreas: () => of([]),
      getTemas: () => of([]),
      getDiccionario: () => of([]),
      obtenerHojas: (archivo: File) => {
        archivosConsultados.push(archivo);
        const respuesta = new Subject<any>();
        hojasPendientes.push(respuesta);
        return respuesta.asObservable();
      },
      subirExcel: (idArea, idTema, archivo, hoja) => {
        cargasSolicitadas.push({ idArea, idTema, archivo, hoja });
        const respuesta = new Subject<any>();
        cargasPendientes.push(respuesta);
        return respuesta.asObservable();
      },
    };

    await TestBed.configureTestingModule({
      imports: [CargaExcelComponent],
      providers: [{ provide: CargaExcelService, useValue: service }],
    }).compileComponents();

    fixture = TestBed.createComponent(CargaExcelComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('reinicia tema y estado de carga al cambiar el área', () => {
    prepararEstadoCargado();
    component.onAreaChange('2');

    expect(component.idArea).toBe(2);
    expect(component.idTema).toBeNull();
    expect(component.archivo).toBeNull();
    expect(component.hojas).toEqual([]);
    expect(component.hojaSeleccionada).toBe('');
    expect(component.progress).toBe(0);
    expect(component.mensaje).toBe('');
    expect(component.isLoading).toBe(false);
  });

  it('conserva el área y el nuevo tema, pero reinicia la carga', () => {
    prepararEstadoCargado();
    component.onTemaChange('20');

    expect(component.idArea).toBe(1);
    expect(component.idTema).toBe(20);
    expect(component.archivo).toBeNull();
    expect(component.hojas).toEqual([]);
    expect(component.hojaSeleccionada).toBe('');
    expect(component.progress).toBe(0);
    expect(component.mensaje).toBe('');
  });

  it('al seleccionar otro archivo limpia hojas, mensaje y progreso anteriores', () => {
    component.idArea = 1;
    component.idTema = 10;
    component.hojas = ['Anterior'];
    component.hojaSeleccionada = 'Anterior';
    component.progress = 100;
    component.mensaje = 'Carga anterior correcta';
    const nuevoArchivo = crearArchivo('nuevo.xlsx');

    component.onFileChange({ target: { files: [nuevoArchivo] } });

    expect(component.archivo).toBe(nuevoArchivo);
    expect(component.hojas).toEqual([]);
    expect(component.hojaSeleccionada).toBe('');
    expect(component.progress).toBe(0);
    expect(component.mensaje).toBe('');
    expect(archivosConsultados).toEqual([nuevoArchivo]);
  });

  it('ignora una respuesta tardía de hojas del archivo anterior', () => {
    const primero = crearArchivo('primero.xlsx');
    const segundo = crearArchivo('segundo.xlsx');
    component.onFileChange({ target: { files: [primero] } });
    component.onFileChange({ target: { files: [segundo] } });

    hojasPendientes[0].next({ hojas: ['Hoja anterior'] });
    expect(component.hojas).toEqual([]);
    hojasPendientes[1].next({ hojas: ['Hoja nueva'] });
    expect(component.hojas).toEqual(['Hoja nueva']);
  });

  it('permite seleccionar nuevamente el mismo archivo después del reinicio', () => {
    const archivo = crearArchivo('mismo.xlsx');
    component.idArea = 1;
    component.idTema = 10;
    component.onFileChange({ target: { files: [archivo] } });

    component.onTemaChange('11');
    component.onFileChange({ target: { files: [archivo] } });

    expect(archivosConsultados).toEqual([archivo, archivo]);
    expect(component.archivo).toBe(archivo);
  });

  it('cambiar de tema cancela una carga pendiente y limpia su estado', () => {
    component.idArea = 1;
    component.idTema = 10;
    component.archivo = crearArchivo('datos.xlsx');
    component.hojaSeleccionada = 'Datos';
    component.onSubmit();
    expect(component.isLoading).toBe(true);

    component.onTemaChange('11');
    cargasPendientes[0].next({
      total_registros: 20,
      archivo: 'datos.xlsx',
      carpeta: 'Anterior',
    });

    expect(component.idTema).toBe(11);
    expect(component.isLoading).toBe(false);
    expect(component.progress).toBe(0);
    expect(component.mensaje).toBe('');
  });

  it('limpia un error anterior al cambiar de tema', () => {
    component.idArea = 1;
    component.idTema = 10;
    component.mensaje = 'Columnas inválidas';
    component.onTemaChange('11');
    expect(component.mensaje).toBe('');
  });

  it('habilita subir únicamente con área, tema, archivo y hoja', () => {
    const boton = () =>
      fixture.nativeElement.querySelector('button.btn-custom') as HTMLButtonElement;

    expect(boton().disabled).toBe(true);
    component.idArea = 1;
    component.idTema = 10;
    component.archivo = crearArchivo('datos.xlsx');
    fixture.detectChanges();
    expect(boton().disabled).toBe(true);

    component.hojaSeleccionada = 'Datos';
    fixture.detectChanges();
    expect(boton().disabled).toBe(false);
  });

  it('evita solicitudes de carga duplicadas mientras está procesando', () => {
    component.idArea = 1;
    component.idTema = 10;
    component.archivo = crearArchivo('datos.xlsx');
    component.hojaSeleccionada = 'Datos';

    component.onSubmit();
    component.onSubmit();

    expect(cargasSolicitadas.length).toBe(1);
  });

  function prepararEstadoCargado(): void {
    component.idArea = 1;
    component.idTema = 10;
    component.archivo = crearArchivo('anterior.xlsx');
    component.hojas = ['Datos'];
    component.hojaSeleccionada = 'Datos';
    component.progress = 100;
    component.mensaje = 'Archivo validado y guardado correctamente.';
    component.isLoading = true;
  }

  function crearArchivo(nombre: string): File {
    return new File(['contenido'], nombre, {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
  }
});
