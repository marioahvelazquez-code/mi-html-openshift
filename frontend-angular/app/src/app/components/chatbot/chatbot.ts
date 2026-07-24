import { ChangeDetectorRef, Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatCardModule } from '@angular/material/card';
import { LucideAngularModule } from 'lucide-angular';

import { forkJoin, Observable, of } from 'rxjs';
import { catchError, debounceTime, map, switchMap } from 'rxjs/operators';

interface Hospital {
  id: string;
  nombre_original: string;
  desc_original?: string;
  descripcion?: string;
}

interface VariableMedica {
  id: string;
  descripcion: string;
}

type SugerenciaAutocomplete =
  (Hospital & { tipo: 'hospital' }) | (VariableMedica & { tipo: 'variable' });

interface ContextoConversacion {
  hospital?: Hospital | null;
  ambito?: any | null;
  hospitalConfirmadoPorUsuario?: boolean;
  region?: any | null;
  entidad?: any | null;
  delegacion?: any | null;
  nivelAtencion?: any | null;
  nivel_atencion?: any | null;
  variable?: any | null;
  variableConfirmadaPorUsuario?: boolean;
  variablesConfirmadas?: any[] | null;
  variables_confirmadas?: any[] | null;
  filtros?: any;
  ultimaConsultaAnalitica?: any | null;
  consultaAnaliticaPendiente?: any | null;
  operacion?: string | null;
  tipoUnidad?: string | null;
  resultadoAnalitico?: any | null;
}

interface ConsultaEnEdicion {
  hospital: Hospital | null;
  variable: VariableMedica | null;
}

interface CandidatoChatbot {
  id: string;
  descripcion: string;
  score: number;
}

interface ResultadoBusqueda {
  status:
    | 'sin_texto'
    | 'baja_confianza'
    | 'empate_tecnico'
    | 'varias_opciones'
    | 'ganador_claro'
    | 'sin_intencion'
    | 'falta_variable'
    | 'falta_ambito';
  hospital?: any;
  ambito_macro?: any;
  variable?: any;
  score: number;
  texto_usado: string;
  candidatos?: CandidatoChatbot[];
}

interface RespuestaChatbot {
  ok: boolean;
  status?: string;
  mensaje?: string;
  respuesta?: string;
  pregunta_original: string;
  contexto: ContextoConversacion;
  hospital: ResultadoBusqueda;
  variable: ResultadoBusqueda;
  datos?: any[];
  requiereConfirmacion?: boolean;
  resetConversacion?: boolean;
  tipoConsulta?: 'CONSULTA_IFU' | 'COUNT_UNIDADES' | 'EXTREMO_POR_UNIDAD' | string;
  operacion?: string;
  tipoUnidad?: string;
  descripcionTipoUnidad?: string;
  nivelesAtencion?: string[];
  ambito?: any;
  totalUnidades?: number;
  variableAnalitica?: any;
  valorExtremo?: number | null;
  totalEmpates?: number;
  resultadosAnaliticos?: any[];
  resultadoAnalitico?: any;
}

interface ResumenConsulta {
  tipoConsulta: string;
  objetivo: string;
  alcance: string;
  resultadoPrincipal: string;
  resultadoSecundario?: string;
  interpretacion: {
    operacion?: string;
    tipoUnidad?: string;
    variable?: string;
    ambito?: string;
    hospital?: string;
  };
}

interface MensajeChat {
  emisor: 'usuario' | 'bot';
  texto: string;
  isAmbiguous?: boolean;
  hospitalesOptions?: CandidatoChatbot[];
  variablesOptions?: CandidatoChatbot[];
  hospitalSeleccionadoId?: string | null;
  variableSeleccionadaId?: string | null;
  confirmado?: boolean;
}

@Component({
  selector: 'app-chat',
  templateUrl: './chatbot.html',
  styleUrls: ['./chatbot.css'],
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatAutocompleteModule,
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    MatCardModule,
    LucideAngularModule,
  ],
})
export class ChatComponent implements OnInit {
  @ViewChild('chatMessages') private chatMessages?: ElementRef<HTMLDivElement>;

  chatControl = new FormControl('');
  sugerenciasFiltradas!: Observable<SugerenciaAutocomplete[]>;
  contexto: ContextoConversacion = {
    hospital: null,
    hospitalConfirmadoPorUsuario: false,
    variableConfirmadaPorUsuario: false,
  };
  consultaEnEdicion: ConsultaEnEdicion = {
    hospital: null,
    variable: null,
  };
  resultados: any[] = [];
  resultadoDeteccion: RespuestaChatbot | null = null;
  resumenConsulta: ResumenConsulta | null = null;
  private textoPreguntaActual = '';
  private textoGeneradoPorSeleccion = false;

  historial: MensajeChat[] = [
    {
      emisor: 'bot',
      texto: 'Hola. ¿Cómo puedo ayudarte hoy con el Inventario Físico de Unidades (IFU)?',
    },
    {
      emisor: 'bot',
      texto:
        'Tip: Conforme escribas, puedes seleccionar las opciones del menú desplegable para guiarte mejor.',
    },
    {
      emisor: 'bot',
      texto:
        'Tip: Puedes preguntarme cosas como :\n- "¿Cuántas camas censables tiene el HGZ 1 Durango?"\n- "¿Cuántos hospitales hay en Sonora?"\n- "¿Cuántas UMFS hay en la región norte?"\n- "¿Cuál hospital tiene más tomógrafos en la región Occidente?"',
    },
  ];

  private API_URL = '/api/catalogos';

  constructor(
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.sugerenciasFiltradas = this.chatControl.valueChanges.pipe(
      debounceTime(300),
      switchMap((value) => {
        const buscar = typeof value === 'string' ? value : '';
        if (typeof value === 'string') {
          this.textoPreguntaActual = value;
          this.textoGeneradoPorSeleccion = false;
        }
        if (buscar.length < 3) return of([]);

        // El autocompletado permite cambiar hospital o variable.
        const buscarHospitales$ = this.http
          .get<Hospital[]>(`${this.API_URL}/buscar-hospitales/?q=${encodeURIComponent(buscar)}`)
          .pipe(catchError(() => of([])));

        const buscarVariables$ = this.http
          .get<VariableMedica[]>(
            `${this.API_URL}/buscar-variables/?q=${encodeURIComponent(buscar)}`,
          )
          .pipe(catchError(() => of([])));

        return forkJoin({
          hospitales: buscarHospitales$,
          variables: buscarVariables$,
        }).pipe(
          map(({ hospitales, variables }) => [
            ...hospitales.map((hospital) => ({
              ...hospital,
              tipo: 'hospital' as const,
            })),
            ...variables.map((variable) => ({
              ...variable,
              tipo: 'variable' as const,
            })),
          ]),
        );
      }),
    );
  }

  mostrarSugerencia(opcion: SugerenciaAutocomplete | string): string {
    if (typeof opcion === 'string') return opcion;
    if (!opcion) return '';
    return opcion.tipo === 'hospital' ? opcion.nombre_original : opcion.descripcion;
  }

  alSeleccionarSugerencia(event: any) {
    const opcion = event.option.value as SugerenciaAutocomplete;
    const textoActual =
      typeof this.chatControl.value === 'string'
        ? this.chatControl.value
        : this.textoPreguntaActual;

    // Conserva solo las selecciones visibles.
    if (
      this.consultaEnEdicion.variable &&
      !this.textoContieneSeleccion(textoActual, this.consultaEnEdicion.variable.descripcion)
    ) {
      this.consultaEnEdicion.variable = null;
    }

    if (
      this.consultaEnEdicion.hospital &&
      !this.textoContieneSeleccion(textoActual, this.consultaEnEdicion.hospital.nombre_original)
    ) {
      this.consultaEnEdicion.hospital = null;
    }

    if (opcion.tipo === 'hospital') {
      const hospitalSeleccionado = {
        id: opcion.id,
        nombre_original: opcion.nombre_original,
      };
      this.consultaEnEdicion.hospital = hospitalSeleccionado;
      this.contexto.hospital = hospitalSeleccionado;
      this.contexto.hospitalConfirmadoPorUsuario = true;
    } else {
      const variableSeleccionada = {
        id: opcion.id,
        descripcion: opcion.descripcion,
      };
      this.consultaEnEdicion.variable = variableSeleccionada;
      this.contexto.variable = variableSeleccionada;
      this.contexto.variableConfirmadaPorUsuario = true;
    }

    const textoVisible = this.construirTextoVisibleDesdeConsultaEnEdicion();

    // Crea el resultado inicial del panel derecho.
    if (!this.resultadoDeteccion) {
      this.resultadoDeteccion = {
        ok: true,
        pregunta_original: this.textoPreguntaActual,
        contexto: this.contexto,
        hospital: {
          status: this.contexto.hospital ? 'ganador_claro' : 'sin_texto',
          hospital: this.contexto.hospital,
          score: this.contexto.hospital ? 1 : 0,
          texto_usado: this.contexto.hospital?.nombre_original || '',
        },
        variable: {
          status: this.contexto.variable ? 'ganador_claro' : 'sin_texto',
          variable: this.contexto.variable,
          score: this.contexto.variable ? 1 : 0,
          texto_usado: this.contexto.variable?.descripcion || '',
        },
        datos: [],
      };
    }

    this.actualizarDeteccionVisibleDesdeContexto(this.contexto.hospital, this.contexto.variable);

    this.textoPreguntaActual = textoVisible;
    this.textoGeneradoPorSeleccion = true;
    this.chatControl.setValue(textoVisible, { emitEvent: false });
    this.cdr.detectChanges();
  }
  enviarMensaje() {
    const mensajeTexto = this.chatControl.value;
    const textoVisible =
      typeof mensajeTexto === 'string' ? mensajeTexto.trim() : this.textoPreguntaActual.trim();
    const textoAMostrar = this.textoGeneradoPorSeleccion
      ? this.construirTextoFinalConsulta(textoVisible)
      : textoVisible;
    if (!textoAMostrar) return;

    this.historial.push({ emisor: 'usuario', texto: textoAMostrar });
    this.chatControl.setValue('');
    this.textoPreguntaActual = '';
    this.textoGeneradoPorSeleccion = false;
    this.cdr.detectChanges();
    this.scrollChatAlFinal();

    const payload = {
      pregunta: textoAMostrar,
      contexto: this.contexto,
    };

    this.http.post<RespuestaChatbot>(`${this.API_URL}/chatbot/`, payload).subscribe({
      next: (res) => {
        this.procesarRespuestaBackend(res);
        this.cdr.detectChanges();
        this.scrollChatAlFinal();
      },
      error: () => {
        this.historial.push({
          emisor: 'bot',
          texto: 'Lo siento, ocurrio un error en el servidor.',
        });
        this.cdr.detectChanges();
        this.scrollChatAlFinal();
      },
    });
  }

  // Crea los mensajes y tarjetas de la respuesta.
  procesarRespuestaBackend(res: RespuestaChatbot) {
    if (res?.resetConversacion === true) {
      this.historial.push({
        emisor: 'bot',
        texto:
          res.mensaje ||
          '¡Con gusto! He cerrado la conversación y limpiado el contexto. Puedes iniciar una nueva consulta cuando quieras.',
      });
      this.reiniciarConversacionDespuesDeDespedida();
      this.scrollChatAlFinal();
      return;
    }

    if (!res?.ok) {
      this.historial.push({
        emisor: 'bot',
        texto:
          res?.mensaje ||
          res?.respuesta ||
          'No entendí tu pregunta. Por favor intenta escribir una unidad médica, una variable o una consulta del IFU.',
      });
      this.scrollChatAlFinal();
      return;
    }

    this.resultadoDeteccion = res;
    this.resultados = res.datos || [];
    this.actualizarContextoDesdeRespuesta(res);
    this.resumenConsulta = this.construirResumenConsulta(res);

    const hospitalesOptions = this.obtenerCandidatos(res.hospital);
    const variablesOptions = this.obtenerCandidatos(res.variable);
    const hayCandidatos = hospitalesOptions.length > 0 || variablesOptions.length > 0;
    const requiereSeleccion = Boolean(res.requiereConfirmacion ?? hayCandidatos) && hayCandidatos;

    if (!requiereSeleccion && res.status) {
      this.historial.push({
        emisor: 'bot',
        texto: this.construirMensajeDeteccion(res),
      });
      this.actualizarDeteccionVisibleDesdeContexto(this.contexto.hospital, this.contexto.variable);
      return;
    }

    if (requiereSeleccion) {
      this.historial.push({
        emisor: 'bot',
        texto: this.construirMensajeDeteccion(res),
        isAmbiguous: true,
        hospitalesOptions,
        variablesOptions,
        hospitalSeleccionadoId: res.hospital.hospital?.id || null,
        variableSeleccionadaId: res.variable.variable?.id || null,
        confirmado: false,
      });
      this.actualizarDeteccionVisibleDesdeContexto(this.contexto.hospital, this.contexto.variable);
      return;
    }

    this.historial.push({
      emisor: 'bot',
      texto: this.construirMensajeDeteccion(res),
    });
    this.actualizarDeteccionVisibleDesdeContexto(this.contexto.hospital, this.contexto.variable);
  }

  seleccionarHospitalOpcion(msg: MensajeChat, id: string) {
    if (msg.confirmado) return;
    msg.hospitalSeleccionadoId = msg.hospitalSeleccionadoId === id ? null : id;
    this.cdr.detectChanges();
  }

  seleccionarVariableOpcion(msg: MensajeChat, id: string) {
    if (msg.confirmado) return;
    msg.variableSeleccionadaId = msg.variableSeleccionadaId === id ? null : id;
    this.cdr.detectChanges();
  }

  puedeConfirmarDesambiguacion(msg: MensajeChat): boolean {
    if (msg.confirmado) return false;

    const requiereHospital = (msg.hospitalesOptions?.length || 0) > 0;
    const requiereVariable = (msg.variablesOptions?.length || 0) > 0;

    if (requiereHospital && !msg.hospitalSeleccionadoId) return false;
    if (requiereVariable && !msg.variableSeleccionadaId) return false;

    return requiereHospital || requiereVariable;
  }

  // El backend aún no tiene un endpoint para la consulta final.
  enviarDesambiguacion(msg: MensajeChat) {
    const requiereHospital = (msg.hospitalesOptions?.length || 0) > 0;
    const requiereVariable = (msg.variablesOptions?.length || 0) > 0;

    if (requiereHospital && !msg.hospitalSeleccionadoId) return;
    if (requiereVariable && !msg.variableSeleccionadaId) return;

    const textoAMostrar = this.resultadoDeteccion?.pregunta_original || '';
    if (!textoAMostrar) return;

    const hospitalConfirmado =
      (msg.hospitalSeleccionadoId
        ? this.buscarCandidato(msg.hospitalesOptions, msg.hospitalSeleccionadoId)
        : null) ||
      this.resultadoDeteccion?.hospital.hospital ||
      null;
    const variableConfirmada =
      (msg.variableSeleccionadaId
        ? this.buscarCandidato(msg.variablesOptions, msg.variableSeleccionadaId)
        : null) ||
      this.resultadoDeteccion?.variable.variable ||
      null;

    const hospitalContexto = hospitalConfirmado
      ? {
          id: hospitalConfirmado.id,
          nombre_original:
            hospitalConfirmado.nombre_original ||
            hospitalConfirmado.desc_original ||
            hospitalConfirmado.descripcion ||
            hospitalConfirmado.id,
        }
      : this.contexto.hospital;
    const variableContexto = variableConfirmada
      ? {
          id: variableConfirmada.id,
          descripcion:
            variableConfirmada.descripcion ||
            variableConfirmada.desc_original ||
            variableConfirmada.id,
        }
      : this.contexto.variable;

    // Actualiza el contexto después de confirmar una opción.
    this.contexto = {
      ...this.contexto,
      hospital: hospitalContexto,
      variable: variableContexto,
      hospitalConfirmadoPorUsuario: Boolean(hospitalConfirmado),
      variableConfirmadaPorUsuario: Boolean(variableConfirmada),
    };
    this.actualizarDeteccionVisibleDesdeContexto(hospitalContexto, variableContexto);

    msg.confirmado = true;
    this.historial.push({
      emisor: 'bot',
      texto: `Seleccion confirmada. Hospital: ${msg.hospitalSeleccionadoId}. Variable: ${msg.variableSeleccionadaId}.`,
    });
    this.cdr.detectChanges();
    this.scrollChatAlFinal();

    const payload = {
      pregunta: textoAMostrar,
      contexto: this.contexto,
    };

    this.http.post<RespuestaChatbot>(`${this.API_URL}/chatbot/`, payload).subscribe({
      next: (res) => {
        this.procesarRespuestaBackend(res);
        this.cdr.detectChanges();
        this.scrollChatAlFinal();
      },
      error: () => {
        msg.confirmado = false;
        this.historial.push({
          emisor: 'bot',
          texto: 'Lo siento, ocurrio un error en el servidor.',
        });
        this.cdr.detectChanges();
        this.scrollChatAlFinal();
      },
    });
  }

  buscarCandidato(candidatos: CandidatoChatbot[] | undefined, id: string): CandidatoChatbot | null {
    return candidatos?.find((candidato) => candidato.id === id) || null;
  }

  construirTextoVisibleDesdeConsultaEnEdicion(): string {
    const { hospital, variable } = this.consultaEnEdicion;

    if (variable && hospital) {
      return `${variable.descripcion} en ${hospital.nombre_original}`;
    }

    if (variable) {
      return variable.descripcion;
    }

    if (hospital) {
      return hospital.nombre_original;
    }

    return '';
  }

  construirTextoFinalConsulta(textoLibreActual = ''): string {
    const variable = this.contexto.variable?.descripcion || '';
    const hospital = this.contexto.hospital?.nombre_original || '';
    const textoLibre = this.limpiarTextoLibreRestante(textoLibreActual);
    const textoVisible = (textoLibreActual || '').trim();
    const usaVariableCanonica =
      Boolean(variable) &&
      (!textoVisible || this.textoSeSolapaConSeleccion(textoVisible, variable));
    const partes: string[] = [];

    if (usaVariableCanonica) {
      partes.push(variable);
    } else if (textoLibre) {
      partes.push(textoLibre);
    }

    if (hospital) {
      partes.push(`en ${hospital}`);
    }

    if (!variable && !hospital) {
      return textoLibre;
    }

    return partes.join(' ').replace(/\s+/g, ' ').trim();
  }

  limpiarTextoLibreRestante(texto: string): string {
    let restante = (texto || '').trim();
    const variable = this.contexto.variable?.descripcion;
    const hospital = this.contexto.hospital?.nombre_original;

    for (const valor of [variable, hospital]) {
      if (!valor) continue;
      restante = restante.replace(valor, ' ');
    }

    if (variable && this.textoSeSolapaConSeleccion(restante, variable)) {
      restante = '';
    }

    if (hospital && this.textoSeSolapaConSeleccion(restante, hospital)) {
      restante = '';
    }

    return restante
      .replace(/\b(en\s+)?(hospital|hgz|hgr|hgzmf|umf|umae)\b\s*$/i, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  textoSeSolapaConSeleccion(texto: string, seleccion: string): boolean {
    const tokensTexto = this.tokensComparables(texto);
    if (tokensTexto.length === 0) return false;

    const tokensSeleccion = new Set(this.tokensComparables(seleccion));
    return tokensTexto.some((token) => tokensSeleccion.has(token));
  }

  textoContieneSeleccion(texto: string, seleccion: string): boolean {
    const textoNormalizado = this.normalizarTextoComparacion(texto);
    const seleccionNormalizada = this.normalizarTextoComparacion(seleccion);

    return Boolean(
      textoNormalizado && seleccionNormalizada && textoNormalizado.includes(seleccionNormalizada),
    );
  }

  normalizarTextoComparacion(texto: string): string {
    return (texto || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^\w\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  tokensComparables(texto: string): string[] {
    return texto
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter((token) => token.length >= 3);
  }

  obtenerCandidatos(resultado: ResultadoBusqueda): CandidatoChatbot[] {
    if (resultado.status === 'ganador_claro') return [];
    return resultado.candidatos || [];
  }

  construirMensajeDeteccion(res: RespuestaChatbot): string {
    if (res.mensaje || res.respuesta) {
      return res.mensaje || res.respuesta || '';
    }

    const tieneFiltroValido = Boolean(res.contexto?.hospital || res.contexto?.ambito);
    const tieneVariableValida = Boolean(res.contexto?.variable);
    const tieneDatos = Boolean(res.datos?.length);

    if (tieneFiltroValido && tieneVariableValida && tieneDatos) {
      return [
        'Listo. Encontré la información que solicitaste.',
        '',
        'Los resultados ya están disponibles en el panel derecho.',
        '',
        'Puedes continuar la conversación sin volver a escribir toda la consulta. Solo cambia la unidad médica, el ámbito, la variable o ambos, por ejemplo:',
        '',
        '• "¿Y en el HGZ 13 Matamoros?"',
        '• "¿Y en la región norte?"',
        '• "¿Y camas no censables?"',
      ].join('\n');
    }

    if (tieneFiltroValido && tieneVariableValida && tieneDatos) {
      return [
        'Listo. Encontré la información que solicitaste.',
        '',
        'Los resultados ya están disponibles en el panel derecho.',
        '',
        'Puedes continuar la conversación sin volver a escribir toda la consulta. Solo cambia la unidad médica, la variable o ambas, por ejemplo:',
        '',
        '• "¿Y en el HGZ 13 Matamoros?"',
        '• "¿Y camas no censables?"',
      ].join('\n');
    }

    const hospital = this.descripcionHospital(res.hospital);
    const variable = this.descripcionVariable(res.variable);

    const lineas = [
      `Hospital: ${hospital} (${this.etiquetaStatus(res.hospital.status)}, score ${this.formatearScore(res.hospital.score)})`,
      `Variable: ${variable} (${this.etiquetaStatus(res.variable.status)}, score ${this.formatearScore(res.variable.score)})`,
    ];

    return lineas.join('\n');
  }

  descripcionHospital(resultado: ResultadoBusqueda): string {
    if (resultado.hospital) {
      return (
        resultado.hospital.nombre_original ||
        resultado.hospital.desc_original ||
        resultado.hospital.descripcion ||
        resultado.hospital.id
      );
    }
    return 'sin hospital claro';
  }

  get panelAmbito(): { titulo: string; valor: string } {
    const hospital = this.contexto.hospital;
    if (hospital) {
      return {
        titulo: 'Hospital',
        valor:
          hospital.nombre_original ||
          hospital.desc_original ||
          hospital.descripcion ||
          hospital.id ||
          'Sin ámbito claro',
      };
    }

    const ambito = this.contexto.ambito;
    if (!ambito) {
      return {
        titulo: 'Consulta actual',
        valor: 'Sin ámbito claro',
      };
    }

    const titulosPorTipo: Record<string, string> = {
      HOSPITAL: 'Hospital',
      ENTIDAD: 'Entidad',
      DELEGACION: 'Delegación',
      REGION: 'Región',
      NIVEL_ATENCION: 'Nivel de Atención',
    };
    const tipo = String(ambito.tipo || '').toUpperCase();

    return {
      titulo: titulosPorTipo[tipo] || 'Consulta actual',
      valor:
        ambito.desc_original ||
        ambito.descripcion ||
        ambito.nombre_original ||
        ambito.texto_usado ||
        ambito.id ||
        'Sin ámbito claro',
    };
  }

  descripcionVariable(resultado: ResultadoBusqueda): string {
    if (resultado.variable) {
      return (
        resultado.variable.desc_original || resultado.variable.descripcion || resultado.variable.id
      );
    }
    return 'sin variable clara';
  }

  etiquetaStatus(status: ResultadoBusqueda['status']): string {
    const etiquetas = {
      sin_texto: 'Sin información',
      baja_confianza: 'Requiere revisión',
      empate_tecnico: 'Se necesita confirmar',
      varias_opciones: 'Se necesita confirmar',
      ganador_claro: 'Confirmado',
      sin_intencion: 'Sin consulta',
      falta_variable: 'Falta variable',
      falta_ambito: 'Falta ámbito',
    };

    return etiquetas[status] || status;
  }

  formatearScore(score: number): string {
    return Number(score || 0).toFixed(2);
  }

  valorNumerico(valor: unknown): number {
    const numero =
      typeof valor === 'number'
        ? valor
        : Number(
            String(valor ?? '')
              .replace(/,/g, '')
              .trim(),
          );

    return Number.isFinite(numero) ? numero : 0;
  }

  construirResumenConsulta(res: RespuestaChatbot): ResumenConsulta | null {
    if (!res?.ok || res.resetConversacion) return null;

    const tipoConsulta = this.inferirTipoConsulta(res);
    if (!tipoConsulta) return null;

    const hospital = this.obtenerDescripcion(res.hospital?.hospital || res.contexto?.hospital, [
      'nombre_original',
      'desc_original',
      'descripcion',
    ]);
    const ambitoObjeto = res.ambito || res.contexto?.ambito;
    const ambito = this.descripcionAmbitoResumen(ambitoObjeto);
    const variableObjeto =
      res.variableAnalitica || res.variable?.variable || res.contexto?.variable;
    const variable =
      this.obtenerDescripcion(variableObjeto, ['descripcion', 'desc_original']) ||
      this.obtenerDescripcion(res.datos?.[0], ['descripcion']);
    const tipoUnidad = res.tipoUnidad || res.contexto?.tipoUnidad || '';

    if (tipoConsulta === 'COUNT_UNIDADES') {
      const esUmf = tipoUnidad === 'UMF';
      const total = Number(res.totalUnidades ?? res.resultadoAnalitico?.total ?? 0);
      const etiquetaResultado = esUmf ? 'UMF' : total === 1 ? 'hospital' : 'hospitales';
      return {
        tipoConsulta: 'Conteo de unidades',
        objetivo: esUmf ? 'Unidades de Medicina Familiar' : 'Hospitales',
        alcance: ambito || 'Ámbito seleccionado',
        resultadoPrincipal: `${total.toLocaleString('es-MX')} ${etiquetaResultado}`,
        interpretacion: {
          operacion: 'Contar',
          tipoUnidad: esUmf ? 'UMF' : 'Hospital',
          ...(ambito ? { ambito } : {}),
        },
      };
    }

    if (tipoConsulta === 'EXTREMO_POR_UNIDAD') {
      const esMaximo = res.operacion === 'MAX';
      const resultados = res.resultadosAnaliticos || res.resultadoAnalitico?.resultados || [];
      const primerResultado = resultados[0] || {};
      const denominacion = this.obtenerDescripcion(primerResultado, [
        'denominacionUnidad',
        'denominacion_unidad',
        'clavePresupuestal',
        'clave_presupuestal',
      ]);
      const valor = res.valorExtremo ?? res.resultadoAnalitico?.valorExtremo;
      const variableCorta = this.descripcionCortaVariable(variable);
      const totalEmpates = Number(res.totalEmpates ?? resultados.length ?? 0);
      return {
        tipoConsulta: esMaximo ? 'Máximo por unidad' : 'Mínimo por unidad',
        objetivo: `${tipoUnidad || 'Unidad'} con ${esMaximo ? 'más' : 'menos'} ${variableCorta.toLowerCase()}`,
        alcance: ambito || 'Ámbito seleccionado',
        resultadoPrincipal:
          totalEmpates > 1
            ? `${totalEmpates} unidades empatadas`
            : denominacion || 'Sin resultados',
        ...(valor !== null && valor !== undefined
          ? {
              resultadoSecundario: `${valor.toLocaleString('es-MX')} ${variableCorta.toLowerCase()}`,
            }
          : {}),
        interpretacion: {
          operacion: esMaximo ? 'Máximo' : 'Mínimo',
          ...(tipoUnidad
            ? { tipoUnidad: tipoUnidad === 'HOSPITAL' ? 'Hospital' : tipoUnidad }
            : {}),
          ...(variable ? { variable } : {}),
          ...(ambito ? { ambito } : {}),
        },
      };
    }

    const fila = res.datos?.[0];
    const valor = fila?.valor;
    return {
      tipoConsulta: 'Consulta IFU',
      objetivo: variable || 'Variable IFU',
      alcance: hospital || ambito || 'Ámbito seleccionado',
      resultadoPrincipal:
        valor === null || valor === undefined
          ? 'Sin resultado'
          : this.valorNumerico(valor).toLocaleString('es-MX'),
      interpretacion: {
        operacion: 'Consultar valor',
        ...(hospital ? { hospital } : {}),
        ...(variable ? { variable } : {}),
        ...(!hospital && ambito ? { ambito } : {}),
      },
    };
  }

  private inferirTipoConsulta(res: RespuestaChatbot): string | null {
    if (res.tipoConsulta) return res.tipoConsulta;
    if ((res.datos || []).length > 0 || res.contexto?.variable) return 'CONSULTA_IFU';
    return null;
  }

  private obtenerDescripcion(objeto: any, campos: string[]): string {
    if (!objeto || typeof objeto !== 'object') return '';
    for (const campo of campos) {
      const valor = objeto[campo];
      if (valor !== null && valor !== undefined && String(valor).trim()) {
        return String(valor).trim();
      }
    }
    return '';
  }

  private descripcionAmbitoResumen(ambito: any): string {
    if (!ambito) return '';
    if (String(ambito.tipo || '').toUpperCase() === 'NACIONAL') return 'Nacional';
    return this.obtenerDescripcion(ambito, [
      'descripcion',
      'desc_original',
      'nombre',
      'nombre_original',
      'texto_usado',
    ]);
  }

  private descripcionCortaVariable(descripcion: string): string {
    if (!descripcion) return 'la variable seleccionada';
    return descripcion
      .replace(/^total\s+de\s+/i, '')
      .replace(/\s+de\s+la\s+unidad\.?$/i, '')
      .replace(/\.$/, '')
      .trim();
  }

  limpiarEstadoConversacional(): void {
    this.contexto = {
      hospital: null,
      variable: null,
      ambito: null,
      hospitalConfirmadoPorUsuario: false,
      variableConfirmadaPorUsuario: false,
      ultimaConsultaAnalitica: null,
      consultaAnaliticaPendiente: null,
      operacion: null,
      tipoUnidad: null,
      resultadoAnalitico: null,
    };
    this.consultaEnEdicion = { hospital: null, variable: null };
    this.resultados = [];
    this.resultadoDeteccion = null;
    this.resumenConsulta = null;
    this.textoPreguntaActual = '';
    this.textoGeneradoPorSeleccion = false;
    this.chatControl.setValue('', { emitEvent: false });
    this.historial.forEach((mensaje) => {
      mensaje.isAmbiguous = false;
      mensaje.hospitalesOptions = [];
      mensaje.variablesOptions = [];
      mensaje.hospitalSeleccionadoId = null;
      mensaje.variableSeleccionadaId = null;
    });
  }

  limpiarHistorialChat(): void {
    this.historial = [
      {
        emisor: 'bot',
        texto: 'Hola. ¿Cómo puedo ayudarte hoy con el Inventario Físico de Unidades (IFU)?',
      },
      {
        emisor: 'bot',
        texto:
          'Tip: Conforme escribas, puedes seleccionar las opciones del menú desplegable para guiarte mejor.',
      },
      {
        emisor: 'bot',
        texto:
          'Tip: Puedes preguntarme cosas como :\n- "¿Cuántas camas censables tiene el HGZ 1 Durango?"\n- "¿Cuántos hospitales hay en Sonora?"\n- "¿Cuántas UMFS hay en la región norte?"\n- "¿Cuál hospital tiene más tomógrafos en la región Occidente?"',
      },
    ];
  }

  limpiarConversacion(): void {
    this.limpiarEstadoConversacional();
    this.limpiarHistorialChat();
    this.cdr.detectChanges();
  }

  private reiniciarConversacionDespuesDeDespedida(): void {
    this.limpiarEstadoConversacional();
  }

  scrollChatAlFinal() {
    setTimeout(() => {
      const contenedor = this.chatMessages?.nativeElement;
      if (!contenedor) return;

      if (typeof contenedor.scrollTo === 'function') {
        contenedor.scrollTo({
          top: contenedor.scrollHeight,
          behavior: 'smooth',
        });
      } else {
        contenedor.scrollTop = contenedor.scrollHeight;
      }
    });
  }

  actualizarContextoDesdeRespuesta(res: RespuestaChatbot) {
    this.contexto = {
      ...this.contexto,
      ...(res.contexto || {}),
    };

    const ambitoRespuesta = res.hospital?.ambito_macro || res.contexto?.ambito;

    // Conserva el valor anterior si no hay un ganador claro.
    if (res.hospital?.status === 'ganador_claro' && res.hospital.hospital) {
      this.contexto.hospital = {
        id: res.hospital.hospital.id,
        nombre_original:
          res.hospital.hospital.nombre_original ||
          res.hospital.hospital.desc_original ||
          res.hospital.hospital.descripcion ||
          res.hospital.hospital.id,
      };
      this.contexto.ambito = null;
    } else if (res.hospital?.status === 'ganador_claro' && ambitoRespuesta) {
      this.contexto.hospital = null;
      this.contexto.ambito = ambitoRespuesta;
    }

    if (res.variable?.status === 'ganador_claro' && res.variable.variable) {
      this.contexto.variable = {
        id: res.variable.variable.id,
        descripcion:
          res.variable.variable.descripcion ||
          res.variable.variable.desc_original ||
          res.variable.variable.id,
      };
    }

    this.contexto.hospitalConfirmadoPorUsuario = Boolean(
      res.contexto?.hospitalConfirmadoPorUsuario,
    );
    this.contexto.variableConfirmadaPorUsuario = Boolean(
      res.contexto?.variableConfirmadaPorUsuario,
    );
  }

  actualizarDeteccionVisibleDesdeContexto(
    hospital: ContextoConversacion['hospital'],
    variable: ContextoConversacion['variable'],
  ) {
    if (!this.resultadoDeteccion) return;

    this.resultadoDeteccion = {
      ...this.resultadoDeteccion,
      hospital: hospital
        ? {
            ...this.resultadoDeteccion.hospital,
            status: 'ganador_claro',
            hospital,
            score: 1,
            texto_usado: hospital.nombre_original || hospital.id,
          }
        : {
            ...this.resultadoDeteccion.hospital,
            status: 'sin_texto',
            hospital: null,
            score: 0,
            texto_usado: '',
          },
      variable: variable
        ? {
            ...this.resultadoDeteccion.variable,
            status: 'ganador_claro',
            variable,
            score: 1,
            texto_usado: variable.descripcion || variable.id,
          }
        : {
            ...this.resultadoDeteccion.variable,
            status: 'sin_texto',
            variable: null,
            score: 0,
            texto_usado: '',
          },
    };
  }
}
