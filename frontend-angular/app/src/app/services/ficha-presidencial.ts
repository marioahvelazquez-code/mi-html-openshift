import { Injectable } from '@angular/core';
import { HttpClient, HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class FichaPresidencialService {
  private apiUrl = '/api/catalogos';

  constructor(private http: HttpClient) {}

  generarFicha(claveEntidad: string): Observable<HttpResponse<Blob>> {
    return this.http.get(`${this.apiUrl}/getGeneraFichaPresidencial/?cveEntidad=${encodeURIComponent(claveEntidad)}`, {
      observe: 'response',
      responseType: 'blob',
    });
  }
}