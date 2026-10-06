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

  it('muestra la clasificación UMAE en una consulta IFU por entidad', () => {
    const respuesta = respuestaIfuAmbito(
      'ENTIDAD',
      'Ciudad de México',
      undefined,
      'Sala de Quirófano',
    );
    respuesta.filtroUmae = true;
    respuesta.contexto.filtroUmae = true;
    respuesta.datos = [{ valor: 105, descripcion: 'Sala de Quirófano' }];

    component.procesarRespuestaBackend(respuesta);
    fixture.detectChanges();

    expect(component.resumenConsulta?.tipoConsulta).toBe('Consulta IFU');
    expect(component.resumenConsulta?.objetivo).toBe('Sala de Quirófano');
    expect(component.resumenConsulta?.alcance).toBe('Ciudad de México');
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('105');
    expect(component.resumenConsulta?.interpretacion.clasificacion).toBe('UMAE');
    expect(fixture.nativeElement.textContent).toContain('Clasificación');
  });

  it('muestra la clasificación UMAE en una consulta IFU nacional', () => {
    const respuesta = respuestaIfuAmbito(
      'NACIONAL',
      'Nacional',
      undefined,
      'Sala de Quirófano',
    );
    respuesta.filtroUmae = true;
    respuesta.contexto.filtroUmae = true;
    respuesta.datos = [{ valor: 253, descripcion: 'Sala de Quirófano' }];

    component.procesarRespuestaBackend(respuesta);

    expect(component.resumenConsulta?.alcance).toBe('Nacional');
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('253');
    expect(component.resumenConsulta?.interpretacion.ambito).toBe('Nacional');
    expect(component.resumenConsulta?.interpretacion.clasificacion).toBe('UMAE');
  });

  it('representa un conteo UMAE por entidad sin duplicar clasificación', () => {
    const respuesta = respuestaCount(null, 'Ciudad de México', 9);
    respuesta.filtroUmae = true;
    respuesta.contexto.filtroUmae = true;
    respuesta.resultadoAnalitico = { total: 9, unidad: 'UMAE' };

    component.procesarRespuestaBackend(respuesta);

    expect(component.resumenConsulta?.objetivo).toBe('UMAE');
    expect(component.resumenConsulta?.alcance).toBe('Entidad · Ciudad de México');
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('9 UMAE');
    expect(component.resumenConsulta?.interpretacion.tipoUnidad).toBe('UMAE');
    expect(component.resumenConsulta?.interpretacion.clasificacion).toBeUndefined();
  });

  it('representa un conteo UMAE nacional', () => {
    const respuesta = respuestaCount(null, 'Nacional', 25, 'NACIONAL');
    respuesta.filtroUmae = true;
    respuesta.contexto.filtroUmae = true;

    component.procesarRespuestaBackend(respuesta);

    expect(component.resumenConsulta?.objetivo).toBe('UMAE');
    expect(component.resumenConsulta?.alcance).toBe('Nacional');
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('25 UMAE');
    expect(component.resumenConsulta?.interpretacion.tipoUnidad).toBe('UMAE');
  });

  it('mantiene UMAE como etiqueta cuando el conteo total es uno', () => {
    const respuesta = respuestaCount(null, 'Nacional', 1, 'NACIONAL');
    respuesta.filtroUmae = true;

    component.procesarRespuestaBackend(respuesta);

    expect(component.resumenConsulta?.resultadoPrincipal).toBe('1 UMAE');
  });

  it('muestra simultáneamente nivel y clasificación UMAE', () => {
    const respuesta = respuestaIfuAmbito(
      'ENTIDAD',
      'Ciudad de México',
      'Tercer Nivel',
      'Sala de Quirófano',
    );
    respuesta.filtroUmae = true;
    respuesta.datos = [{ valor: 105, descripcion: 'Sala de Quirófano' }];

    component.procesarRespuestaBackend(respuesta);

    expect(component.resumenConsulta?.interpretacion.nivel).toBe('Tercer Nivel');
    expect(component.resumenConsulta?.interpretacion.clasificacion).toBe('UMAE');
  });

  it('no muestra clasificación cuando filtroUmae es falso o no existe', () => {
    const respuestaConFiltroFalso = respuestaIfuAmbito(
      'ENTIDAD',
      'Ciudad de México',
    );
    respuestaConFiltroFalso.filtroUmae = false;
    respuestaConFiltroFalso.contexto.filtroUmae = true;

    component.procesarRespuestaBackend(respuestaConFiltroFalso);

    expect(component.resumenConsulta?.interpretacion.clasificacion).toBeUndefined();

    component.procesarRespuestaBackend(
      respuestaIfuAmbito('ENTIDAD', 'Ciudad de México'),
    );

    expect(component.resumenConsulta?.interpretacion.clasificacion).toBeUndefined();
  });

  it('representa un conteo genérico sin convertirlo en hospitales', () => {
    component.procesarRespuestaBackend(
      respuestaCount(null, 'Querétaro', 22, 'OOAD', ['Primer Nivel']),
    );

    expect(component.resumenConsulta?.objetivo).toBe('Unidades');
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('22 unidades');
    expect(component.resumenConsulta?.interpretacion.tipoUnidad).toBe('Todas las unidades');
    expect(component.resumenConsulta?.alcance).toBe('OOAD · Querétaro');
    expect(component.resumenConsulta?.interpretacion.ambito).toBe('OOAD · Querétaro');
    expect(component.resumenConsulta?.interpretacion.nivel).toBe('Primer Nivel');
  });

  it('muestra ámbito y nivel en una consulta IFU por entidad', () => {
    component.procesarRespuestaBackend(
      respuestaIfuAmbito('ENTIDAD', 'Ciudad de México', 'Tercer Nivel'),
    );

    expect(component.resumenConsulta?.interpretacion.ambito).toBe('Ciudad de México');
    expect(component.resumenConsulta?.interpretacion.nivel).toBe('Tercer Nivel');
  });

  it('omite el nivel en una consulta IFU por entidad sin nivel explícito', () => {
    component.procesarRespuestaBackend(
      respuestaIfuAmbito('ENTIDAD', 'Ciudad de México'),
    );

    expect(component.resumenConsulta?.interpretacion.ambito).toBe('Ciudad de México');
    expect(component.resumenConsulta?.interpretacion.nivel).toBeUndefined();
  });

  it('muestra solo Nivel en la interpretación cuando el ámbito es NIVEL_ATENCION', () => {
    component.procesarRespuestaBackend(
      respuestaIfuAmbito('NIVEL_ATENCION', 'Tercer Nivel', 'Tercer Nivel'),
    );

    expect(component.resumenConsulta?.alcance).toBe('Tercer Nivel');
    expect(component.resumenConsulta?.interpretacion.ambito).toBeUndefined();
    expect(component.resumenConsulta?.interpretacion.nivel).toBe('Tercer Nivel');
  });

  it('conserva la etiqueta OOAD y muestra el nivel en consultas IFU', () => {
    component.procesarRespuestaBackend(
      respuestaIfuAmbito('OOAD', 'Querétaro', 'Segundo Nivel'),
    );

    expect(component.resumenConsulta?.alcance).toBe('OOAD · Querétaro');
    expect(component.resumenConsulta?.interpretacion.ambito).toBe('OOAD · Querétaro');
    expect(component.resumenConsulta?.interpretacion.nivel).toBe('Segundo Nivel');
  });

  it('muestra el nivel genéricamente para otra variable IFU', () => {
    component.procesarRespuestaBackend(
      respuestaIfuAmbito(
        'ENTIDAD',
        'Ciudad de México',
        'Tercer Nivel',
        'Sala de Quirófano',
      ),
    );

    expect(component.resumenConsulta?.objetivo).toBe('Sala de Quirófano');
    expect(component.resumenConsulta?.interpretacion.nivel).toBe('Tercer Nivel');
  });

  it('no muestra como nivel explícito la clasificación implícita de UMF', () => {
    component.procesarRespuestaBackend(
      respuestaCount('UMF', 'Jalisco', 35),
    );

    expect(component.resumenConsulta?.interpretacion.nivel).toBeUndefined();
  });

  it('no muestra como nivel explícito la clasificación implícita de hospitales', () => {
    component.procesarRespuestaBackend(
      respuestaCount('HOSPITAL', 'Jalisco', 8),
    );

    expect(component.resumenConsulta?.interpretacion.nivel).toBeUndefined();
  });

  it('no muestra nivel en una consulta nacional sin nivel explícito', () => {
    component.procesarRespuestaBackend(
      respuestaCount(null, 'Nacional', 100, 'NACIONAL', []),
    );

    expect(component.resumenConsulta?.interpretacion.nivel).toBeUndefined();
  });

  it('mantiene singular y plural para unidades genéricas y hospitales', () => {
    component.procesarRespuestaBackend(respuestaCount(null, 'Nacional', 1, 'NACIONAL'));
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('1 unidad');

    component.procesarRespuestaBackend(respuestaCount(null, 'Nacional', 2, 'NACIONAL'));
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('2 unidades');

    component.procesarRespuestaBackend(respuestaCount('HOSPITAL', 'Nacional', 1, 'NACIONAL'));
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('1 hospital');

    component.procesarRespuestaBackend(respuestaCount('HOSPITAL', 'Nacional', 2, 'NACIONAL'));
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('2 hospitales');
  });

  it('representa conteos genéricos igual para todos los tipos de ámbito', () => {
    const ambitos = [
      { tipo: 'OOAD', descripcion: 'Querétaro', alcance: 'OOAD · Querétaro' },
      { tipo: 'ENTIDAD', descripcion: 'Querétaro', alcance: 'Entidad · Querétaro' },
      { tipo: 'DELEGACION', descripcion: 'México Oriente', alcance: 'Delegación · México Oriente' },
      { tipo: 'REGION', descripcion: 'Norte', alcance: 'Región · Norte' },
      { tipo: 'NACIONAL', descripcion: 'Nacional', alcance: 'Nacional' },
    ];

    for (const ambito of ambitos) {
      component.procesarRespuestaBackend(
        respuestaCount(null, ambito.descripcion, 4, ambito.tipo),
      );

      expect(component.resumenConsulta?.objetivo).toBe('Unidades');
      expect(component.resumenConsulta?.interpretacion.tipoUnidad).toBe('Todas las unidades');
      expect(component.resumenConsulta?.resultadoPrincipal).toBe('4 unidades');
      expect(component.resumenConsulta?.alcance).toBe(ambito.alcance);
      expect(component.resumenConsulta?.interpretacion.ambito).toBe(ambito.alcance);
    }
  });

  it('conserva tipos de unidad futuros sin tratarlos como hospitales', () => {
    const respuesta = respuestaCount('OTRO_TIPO', 'Ejemplo', 3);
    respuesta.descripcionTipoUnidad = 'Otro tipo de unidad';
    component.procesarRespuestaBackend(respuesta);

    expect(component.resumenConsulta?.objetivo).toBe('Otro tipo de unidad');
    expect(component.resumenConsulta?.interpretacion.tipoUnidad).toBe('OTRO_TIPO');
    expect(component.resumenConsulta?.resultadoPrincipal).toBe('3 unidades');
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

  function respuestaCount(
    tipoUnidad: string | null,
    descripcionAmbito: string,
    total: number,
    tipoAmbito = 'ENTIDAD',
    nivelesAtencion?: string[],
  ): any {
    return {
      ok: true,
      status: 'ok',
      pregunta_original: 'conteo',
      tipoConsulta: 'COUNT_UNIDADES',
      operacion: 'COUNT',
      tipoUnidad,
      nivelesAtencion:
        nivelesAtencion ??
        (tipoUnidad === 'UMF'
          ? ['Primer Nivel']
          : tipoUnidad === 'HOSPITAL'
            ? ['Segundo Nivel', 'Tercer Nivel']
            : []),
      ambito: { tipo: tipoAmbito, id: 'X', descripcion: descripcionAmbito },
      totalUnidades: total,
      contexto: {
        hospital: null,
        variable: null,
        ambito: { tipo: tipoAmbito, id: 'X', descripcion: descripcionAmbito },
      },
      hospital: sinBusqueda,
      variable: sinBusqueda,
      datos: [],
    };
  }

  function respuestaIfuAmbito(
    tipoAmbito: string,
    descripcionAmbito: string,
    nivel?: string,
    descripcionVariable = 'Total de Camas Censables de la unidad.',
  ): any {
    const nivelAtencion = nivel
      ? {
          tipo: 'NIVEL_ATENCION',
          id: nivel,
          descripcion: nivel,
        }
      : undefined;
    const ambito = {
      tipo: tipoAmbito,
      id: tipoAmbito === 'ENTIDAD' ? '09' : 'X',
      desc_original: descripcionAmbito,
      ...(nivelAtencion ? { nivel_atencion: nivelAtencion } : {}),
    };

    return {
      ok: true,
      pregunta_original: 'consulta IFU por ámbito',
      contexto: {
        hospital: null,
        ambito,
        variable: { id: 50100, descripcion: descripcionVariable },
      },
      hospital: {
        ...sinBusqueda,
        status: 'ganador_claro',
        hospital: null,
        ambito_macro: ambito,
      },
      variable: {
        ...sinBusqueda,
        status: 'ganador_claro',
        variable: { id: 50100, descripcion: descripcionVariable },
      },
      datos: [{ valor: 120, descripcion: descripcionVariable }],
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
