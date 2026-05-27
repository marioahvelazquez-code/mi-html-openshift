import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class CargaExcelService {
  private apiUrl = '/api/catalogos';

  constructor(private http: HttpClient) {}

  getAreas(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/areas/`);
  }

  getTemas(idArea: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/temas/?id_area=${idArea}`);
  }

  getDiccionario(idTema: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/diccionario/?id_tema=${idTema}`);
  }

  subirExcel(idArea: number, idTema: number, archivo: File, hoja: string): Observable<any> {
    const formData = new FormData();
    formData.append('id_area', idArea.toString());
    formData.append('id_tema', idTema.toString());
    formData.append('file', archivo);
    formData.append('hoja', hoja);
    console.log('Archivo a subir:', archivo);
    return this.http.post(`${this.apiUrl}/subir_excel/`, formData);
  }

  obtenerHojas(archivo: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', archivo);

    return this.http.post(`${this.apiUrl}/obtener_hojas_excel/`, formData);
  }
}
