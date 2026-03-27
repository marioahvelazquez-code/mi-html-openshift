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
// Tipos de UI / estado
// =====================

export type VistaActiva =
  | "menu"
  | "inicio"
  | "excel"
  | "dashboard"
  | "consultassql"
  | "RevisaPPTx";
