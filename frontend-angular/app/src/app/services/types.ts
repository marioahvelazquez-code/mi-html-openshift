// =====================
// Datos del backend
// =====================

export interface Area {
  id_area: number;
  nombre: string;
}

export interface Tema {
  id_tema: number;
  nombre: string;
}

export interface DiccionarioCampo {
  id_campo: number;
  columna_excel: string;
  tipo_dato: string;
  obligatorio: boolean;
}
// =====================
// Datos del backend - Ficha Hospitalaria
// =====================
export interface Region {
  id_region: string;
  nombre: string;
}
export interface Entidad {
  id_entidad: string;
  Entidad: string;
}
export interface NivelAtencion {
  id_nivel_atencion: string;
  nombre: string;
}
export interface UnidadMedica {
  id_unidad_medica: string;
  nombre: string;
}

// =====================
// Tipos de UI / estado
// =====================

export type VistaActiva = 'menu' | 'inicio' | 'excel' | 'dashboard' | 'consultassql' | 'RevisaPPTx';
