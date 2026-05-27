import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class BitacoraService {
  private apiUrl = 'http://localhost:8089/api/catalogos';

  constructor(private http: HttpClient) {}

  getBitacora(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/bitacoracarga/`);
  }

  getAreas(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/areas/`);
  }
}
