import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { ChatComponent } from './chatbot';

describe('ChatComponent', () => {
  let component: ChatComponent;
  let fixture: ComponentFixture<ChatComponent>;
  let httpTesting: HttpTestingController;

  const sinBusqueda = {
    status: 'sin_texto',
    score: 0,
    texto_usado: '',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChatComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(ChatComponent);
    component = fixture.componentInstance;
    httpTesting = TestBed.inject(HttpTestingController);
    fixture.detectChanges();

    const fechaRequest = httpTesting.expectOne(
      '/api/catalogos/fecha-corte-ifu/',
    );
    fechaRequest.flush({
      anio: 2026,
      mes: 6,
      mes_nombre: 'Junio',
      fecha_corte: 'Fecha de corte del IFU, Junio de 2026',
    });
    await fixture.whenStable();
    fixture.changeDetectorRef.detectChanges();
  });

  afterEach(() => httpTesting.verify());

  it('crea el componente', () => {
    expect(component).toBeTruthy();
  });

  it('carga y muestra la fecha de corte del IFU al iniciar', () => {
    expect(component.fechaCorteIfu()).toBe(
      'Fecha de corte del IFU, Junio de 2026',
    );

    const leyenda = fixture.nativeElement.querySelector('.fecha-corte-ifu');
    expect(leyenda?.textContent.trim()).toBe(
      'Fecha de corte del IFU, Junio de 2026',
    );
  });

  it('oculta discretamente la fecha si el endpoint falla', () => {
    (component as any).cargarFechaCorteIfu();

    const request = httpTesting.expectOne(
      '/api/catalogos/fecha-corte-ifu/',
    );
    request.flush(
      { error: 'No disponible' },
      { status: 503, statusText: 'Service Unavailable' },
    );
    fixture.changeDetectorRef.detectChanges();

    expect(component.fechaCorteIfu()).toBeNull();
    expect(
      fixture.nativeElement.querySelector('.fecha-corte-ifu'),
    ).toBeNull();
  });

  it('muestra y oculta los alcances del chatbot', () => {
    const boton = fixture.nativeElement.querySelector('.alcances-toggle') as HTMLButtonElement;

    expect(component.mostrarAlcances()).toBe(false);
    expect(boton.getAttribute('aria-expanded')).toBe('false');
    expect(fixture.nativeElement.querySelector('.alcances-chatbot')).toBeNull();

    boton.click();
    fixture.changeDetectorRef.detectChanges();

    expect(component.mostrarAlcances()).toBe(true);
    expect(boton.getAttribute('aria-expanded')).toBe('true');
    expect(
      fixture.nativeElement.querySelector('.alcances-chatbot')?.textContent,
    ).toContain('El asistente consulta información del IFU vigente.');

    boton.click();
    fixture.changeDetectorRef.detectChanges();

    expect(component.mostrarAlcances()).toBe(false);
    expect(fixture.nativeElement.querySelector('.alcances-chatbot')).toBeNull();
  });

  it('construye el resumen de una consulta IFU', () => {
    component.procesarRespuestaBackend({
      ok: true,
      pregunta_original: 'consultorios de la UMF 27',
      contexto: {
        hospital: { id: 'UMF-27', nombre_original: 'UMF 27 Tijuana' },
        variable: { id: '70000', descripcion: 'Total de Consultorios de la Unidad' },
      },
      hospital: {
        ...sinBusqueda,
        status: 'ganador_claro',
        hospital: { id: 'UMF-27', nombre_original: 'UMF 27 Tijuana' },
      } as any,
      variable: {
        ...sinBusqueda,
        status: 'ganador_claro',
        variable: { id: '70000', descripcion: 'Total de Consultorios de la Unidad' },
      } as any,
      datos: [{ valor: 57, descripcion: 'Total de Consultorios de la Unidad' }],
    });

    expect(component.resumenConsulta?.tipoConsulta).toBe('Consulta IFU');
    expect(component.resumenConsulta?.objetivo).toBe('Total de Consultorios de la Unidad');
    expect(component.resumenConsulta?.alcance).toBe('UMF 27 Tijuana');
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('57');
  });

  it('construye el conteo de UMF', () => {
    component.procesarRespuestaBackend(
      respuestaCount('UMF', 'Zacatecas', 35),
    );

    expect(component.resumenConsulta?.objetivo).toBe('Unidades de Medicina Familiar');
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('35 UMF');
    expect(component.resumenConsulta?.interpretacion.tipoUnidad).toBe('UMF');
  });

  it('construye el conteo de hospitales', () => {
    component.procesarRespuestaBackend(
      respuestaCount('HOSPITAL', 'Durango', 8),
    );

    expect(component.resumenConsulta?.objetivo).toBe('Hospitales');
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('8 hospitales');
    expect(component.resumenConsulta?.interpretacion.tipoUnidad).toBe('Hospital');
  });

  it('construye máximos y mínimos por unidad', () => {
    component.procesarRespuestaBackend(respuestaExtremo('MAX'));
    expect(component.resumenConsulta?.tipoConsulta).toBe('Máximo por unidad');
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('UMF 27 Tijuana');
    expect(component.resumenConsulta?.resultadoSecundario).toBe('57 consultorios');

    component.procesarRespuestaBackend(respuestaExtremo('MIN'));
    expect(component.resumenConsulta?.tipoConsulta).toBe('Mínimo por unidad');
    expect(component.resumenConsulta?.interpretacion.operacion).toBe('Mínimo');
  });

  it('una continuación reemplaza el tipo de unidad y el resultado visibles', () => {
    component.procesarRespuestaBackend(
      respuestaCount('HOSPITAL', 'Durango', 8),
    );
    component.procesarRespuestaBackend(
      respuestaCount('UMF', 'Durango', 22),
    );

    expect(component.resumenConsulta?.objetivo).toBe('Unidades de Medicina Familiar');
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('22 UMF');
    expect(component.resumenConsulta?.interpretacion.hospital).toBeUndefined();
    expect(component.resumenConsulta?.interpretacion.variable).toBeUndefined();
  });

  it('una consulta COUNT elimina visualmente los datos IFU anteriores', () => {
    component.resultados = [{ valor: 57, descripcion: 'Consultorios' }];
    component.procesarRespuestaBackend(
      respuestaCount('UMF', 'Zacatecas', 35),
    );

    expect(component.resultados).toEqual([]);
    expect(component.resumenConsulta?.alcance).toBe('Zacatecas');
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('35 UMF');
  });

  it('resetConversacion limpia el panel pero conserva la despedida', () => {
    component.procesarRespuestaBackend(
      respuestaCount('HOSPITAL', 'Durango', 8),
    );
    const mensajesAntes = component.historial.length;

    component.procesarRespuestaBackend({
      ok: true,
      status: 'conversacion_finalizada',
      mensaje: '¡Con gusto! He cerrado la conversación.',
      resetConversacion: true,
      pregunta_original: 'Gracias',
      contexto: {},
      hospital: sinBusqueda as any,
      variable: sinBusqueda as any,
      datos: [],
    });

    expect(component.resumenConsulta).toBeNull();
    expect(component.resultadoDeteccion).toBeNull();
    expect(component.contexto.hospital).toBeNull();
    expect(component.contexto.variable).toBeNull();
    expect(component.historial.length).toBe(mensajesAntes + 1);
    expect(component.historial.at(-1)?.texto).toContain('He cerrado la conversación');
  });

  it('la siguiente petición después del cierre envía contexto vacío', () => {
    component.limpiarEstadoConversacional();
    component.chatControl.setValue('¿Y en Durango?');
    component.enviarMensaje();

    const request = httpTesting.expectOne('/api/catalogos/chatbot/');
    expect(request.request.body.contexto.hospital).toBeNull();
    expect(request.request.body.contexto.variable).toBeNull();
    expect(request.request.body.contexto.ambito).toBeNull();
    expect(request.request.body.contexto.ultimaConsultaAnalitica).toBeNull();
    request.flush({
      ok: false,
      pregunta_original: '¿Y en Durango?',
      contexto: {},
      hospital: sinBusqueda,
      variable: sinBusqueda,
    });
  });

  it('el botón Limpiar reinicia también el historial visual', () => {
    component.historial.push({ emisor: 'usuario', texto: 'Consulta anterior' });
    component.procesarRespuestaBackend(
      respuestaCount('HOSPITAL', 'Durango', 8),
    );

    component.limpiarConversacion();

    expect(component.historial.length).toBe(2);
    expect(component.resumenConsulta).toBeNull();
    expect(component.contexto.ambito).toBeNull();
  });

  function respuestaCount(tipoUnidad: string, descripcionAmbito: string, total: number): any {
    return {
      ok: true,
      status: 'ok',
      pregunta_original: 'conteo',
      tipoConsulta: 'COUNT_UNIDADES',
      operacion: 'COUNT',
      tipoUnidad,
      nivelesAtencion: tipoUnidad === 'UMF' ? ['Primer Nivel'] : ['Segundo Nivel', 'Tercer Nivel'],
      ambito: { tipo: 'ENTIDAD', id: 'X', descripcion: descripcionAmbito },
      totalUnidades: total,
      contexto: {
        hospital: null,
        variable: null,
        ambito: { tipo: 'ENTIDAD', id: 'X', descripcion: descripcionAmbito },
      },
      hospital: sinBusqueda,
      variable: sinBusqueda,
      datos: [],
    };
  }

  function respuestaExtremo(operacion: 'MAX' | 'MIN'): any {
    return {
      ok: true,
      status: 'ok',
      pregunta_original: 'extremo',
      tipoConsulta: 'EXTREMO_POR_UNIDAD',
      operacion,
      tipoUnidad: 'UMF',
      ambito: { tipo: 'NACIONAL', id: 'NACIONAL', descripcion: 'Nacional' },
      variableAnalitica: {
        id: '70000',
        descripcion: 'Total de Consultorios de la Unidad',
      },
      valorExtremo: 57,
      totalEmpates: 1,
      resultadosAnaliticos: [
        { denominacionUnidad: 'UMF 27 Tijuana', valor: 57 },
      ],
      contexto: { hospital: null, variable: null, ambito: { tipo: 'NACIONAL' } },
      hospital: sinBusqueda,
      variable: sinBusqueda,
      datos: [],
    };
  }
});
