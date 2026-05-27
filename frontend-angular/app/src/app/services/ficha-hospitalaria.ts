import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

interface RespuestaFicha {
  ok: boolean;
  url: string;
  pptx_url?: string;
}

@Injectable({ providedIn: 'root' })
export class fichahospitalaria {
  private apiUrl = '/api/catalogos';

  constructor(private http: HttpClient) {}

  getRegion(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/getRegion/`);
  }

  getEntidad(idRegion: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/getEntidad/?idRegion=${idRegion}`);
  }

  getNivelAtencion(idEntidad: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/getNivelAtencion/?idEntidad=${idEntidad}`);
  }

  getUnidad(idEntidad: string, id_nivel_atencion: string): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.apiUrl}/getUnidad/?idEntidad=${idEntidad}&id_nivel_atencion=${id_nivel_atencion}`,
    );
  }

  getFichaHospitalaria(idUnidad: string): Observable<RespuestaFicha> {
    return this.http.get<RespuestaFicha>(`${this.apiUrl}/getGeneraFicha/?idUnidad=${idUnidad}`);
  }
}
