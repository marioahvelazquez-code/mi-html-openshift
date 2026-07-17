IF OBJECT_ID('dbo.sistema_solicitudes_expeciales_bd', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.sistema_solicitudes_expeciales_bd (
        id_solicitud_especial BIGINT IDENTITY(1,1) NOT NULL,
        ticket AS (
            'SEBD-' + RIGHT(REPLICATE('0', 8) + CONVERT(VARCHAR(20), id_solicitud_especial), 8)
        ) PERSISTED,
        nombre_completo NVARCHAR(200) NOT NULL,
        correo NVARCHAR(200) NOT NULL,
        coordinacion NVARCHAR(200) NULL,
        rol NVARCHAR(150) NULL,
        bases_datos_csv NVARCHAR(MAX) NOT NULL,
        tabla NVARCHAR(200) NULL,
        cruce NVARCHAR(2) NULL,
        con_quien_se_cruza NVARCHAR(250) NULL,
        oficio_nombre_archivo NVARCHAR(255) NULL,
        oficio_url NVARCHAR(500) NULL,
        estatus NVARCHAR(30) NOT NULL CONSTRAINT DF_solicitudes_expeciales_bd_estatus DEFAULT ('PENDIENTE'),
        usuario NVARCHAR(150) NULL,
        contrasena NVARCHAR(150) NULL,
        fecha_solicitud DATETIME2(0) NOT NULL CONSTRAINT DF_solicitudes_expeciales_bd_fecha DEFAULT (SYSDATETIME()),
        CONSTRAINT PK_solicitudes_expeciales_bd PRIMARY KEY CLUSTERED (id_solicitud_especial ASC),
        CONSTRAINT CK_solicitudes_expeciales_bd_cruce CHECK (cruce IN ('SI', 'NO') OR cruce IS NULL),
        CONSTRAINT CK_solicitudes_expeciales_bd_cruce_detalle CHECK (
            (cruce = 'SI' AND con_quien_se_cruza IS NOT NULL AND LTRIM(RTRIM(con_quien_se_cruza)) <> '')
            OR (cruce = 'NO' AND con_quien_se_cruza IS NULL)
            OR cruce IS NULL
        )
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
        WHERE name = 'UX_solicitudes_expeciales_bd_ticket'
            AND object_id = OBJECT_ID('dbo.sistema_solicitudes_expeciales_bd')
)
BEGIN
        CREATE UNIQUE NONCLUSTERED INDEX UX_solicitudes_expeciales_bd_ticket
                ON dbo.sistema_solicitudes_expeciales_bd (ticket);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
        WHERE name = 'IX_solicitudes_expeciales_bd_correo_fecha'
            AND object_id = OBJECT_ID('dbo.sistema_solicitudes_expeciales_bd')
)
BEGIN
        CREATE NONCLUSTERED INDEX IX_solicitudes_expeciales_bd_correo_fecha
                ON dbo.sistema_solicitudes_expeciales_bd (correo, fecha_solicitud DESC);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
        WHERE name = 'IX_solicitudes_expeciales_bd_estatus_fecha'
            AND object_id = OBJECT_ID('dbo.sistema_solicitudes_expeciales_bd')
)
BEGIN
        CREATE NONCLUSTERED INDEX IX_solicitudes_expeciales_bd_estatus_fecha
                ON dbo.sistema_solicitudes_expeciales_bd (estatus, fecha_solicitud DESC);
END;
