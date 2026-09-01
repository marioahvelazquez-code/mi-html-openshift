from django.db import connection


class ConsultaIFU:
    def obtener_fecha_corte(self):
        query = """
            SELECT TOP 1
                [Año] AS anio,
                [Mes] AS mes
            FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual]
            WHERE [Año] IS NOT NULL
              AND [Mes] IS NOT NULL
            ORDER BY [Año] DESC, [Mes] DESC
        """

        with connection.cursor() as cursor:
            cursor.execute(query)
            fila = cursor.fetchone()

        if not fila:
            return None

        return {
            "anio": int(fila[0]),
            "mes": int(fila[1]),
        }

    def obtener_valor_dinamico(self, tipo_ambito, filtro_id, variable_id):
        tipo_ambito = (tipo_ambito or "").upper()
        parametros = [variable_id]

        if tipo_ambito == "NACIONAL":
            campo_select = "'NACIONAL'"
            campo_alias = "ambito"
            filtro_sql = ""

        elif tipo_ambito == "ENTIDAD":
            campo_select = "b.ClaveEntidadFederativa"
            campo_alias = "ClaveEntidadFederativa"
            filtro_sql = "AND b.ClaveEntidadFederativa = %s"
            parametros.append(filtro_id)

        elif tipo_ambito == "DELEGACION":
            campo_select = "b.NombreDelegacionUMAE"
            campo_alias = "NombreDelegacionUMAE"
            filtro_sql = "AND b.Cve_Deleg_UMAE = %s"
            parametros.append(filtro_id)

        elif tipo_ambito == "REGION":
            campo_select = "b.Region"
            campo_alias = "Region"
            filtro_sql = "AND b.Region = %s"
            parametros.append(filtro_id)

        elif tipo_ambito == "NIVEL_ATENCION":
            campo_select = "b.NivelAtencion"
            campo_alias = "NivelAtencion"
            filtro_sql = "AND b.NivelAtencion = %s"
            parametros.append(filtro_id)

        else:
            raise ValueError(f"Tipo de ambito no soportado: {tipo_ambito}")

        group_by = ""
        if tipo_ambito != "NACIONAL":
            group_by = f"""
                GROUP BY
                    {campo_select},
                    a.variable_nva,
                    a.descripcion
            """
        else:
            group_by = """
                GROUP BY
                    a.variable_nva,
                    a.descripcion
            """

        query = f"""
            SELECT
                {campo_select} AS {campo_alias},
                a.variable_nva,
                a.descripcion,
                SUM(TRY_CONVERT(decimal(18, 2), REPLACE(a.valor, ',', ''))) AS valor,
                COUNT(DISTINCT b.ClavePresupuestal) AS total_unidades
            FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual] a
            JOIN [DB_Catalogos].[dbo].[CUMM_ACTUAL] b
                ON a.CvePresupuestal = b.ClavePresupuestal
                COLLATE Modern_Spanish_CI_AS
            WHERE a.variable_nva = %s
            {filtro_sql}
            {group_by}
        """

        with connection.cursor() as cursor:
            cursor.execute(query, parametros)
            columnas = [col[0] for col in cursor.description]
            filas = cursor.fetchall()

        return [
            dict(zip(columnas, fila))
            for fila in filas
        ]
    def obtener_valor(self, clave_unidad, variable_id):
        # query = """
        #     SELECT
        #         ClavePresupuestal,
        #         Region,
        #         NombreDelegacionUMAE,
        #         NivelAtencion,
        #         DenominacionUnidad,
        #         variable_nva,
        #         descripcion,
        #         valor
        #     FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual] a
        #     JOIN [DB_Catalogos].[dbo].[CUMM_ACTUAL] b
        #         ON a.CvePresupuestal = b.ClavePresupuestal
        #         COLLATE Modern_Spanish_CI_AS
        #     WHERE variable_nva = %s
        #       AND ClavePresupuestal = %s
        # """
        query = """
            SELECT
                a.ClavePresupuestal,
                b.Region,
                b.NombreDelegacionUMAE,
                b.NivelAtencion,
                b.DenominacionUnidad,
                a.variable_nva,
                a.descripcion,
                a.valor
            FROM
            (
                SELECT
                    CvePresupuestal AS ClavePresupuestal,
                    variable_nva,
                    descripcion,
                    valor
                FROM [DB_Catalogos].[dbo].[Cat_IFU_Actual]
                WHERE variable_nva =  %s
                AND CvePresupuestal = %s
            ) a
            INNER JOIN [DB_Catalogos].[dbo].[CUMM_ACTUAL] b
                ON a.ClavePresupuestal =
                b.ClavePresupuestal COLLATE Modern_Spanish_CI_AS;
       """

        with connection.cursor() as cursor:
            cursor.execute(query, [variable_id, clave_unidad])
            columnas = [col[0] for col in cursor.description]
            filas = cursor.fetchall()

        return [
            dict(zip(columnas, fila))
            for fila in filas
        ]
