
use DB_FichaEstatal

go
CREATE TABLE cat_area (
    id_area INT IDENTITY PRIMARY KEY,
    nombre NVARCHAR(100) NOT NULL,
    descripcion NVARCHAR(255),
    activo BIT NOT NULL DEFAULT 1,
    fecha_creacion DATETIME2 DEFAULT SYSDATETIME()
);
insert into cat_area(nombre, descripcion) values('Catálogos','Carga de Catálogos')
insert into cat_area(nombre, descripcion) values('DIR','Dirección de Incorporación y Recaudación')
insert into cat_area(nombre, descripcion) values('DPES','Dirección de Prestaciones Económicas y Sociales')
insert into cat_area(nombre, descripcion) values('DPTI','Dirección de Planeación para la Transformación Institucional')
insert into cat_area(nombre, descripcion) values('Personal','Personal')
insert into cat_area(nombre, descripcion) values('DA','Dirección Administrativa')

--select * from cat_area 

CREATE TABLE cat_tema (
    id_tema INT IDENTITY PRIMARY KEY,
    id_area INT NOT NULL,
    nombre NVARCHAR(150) NOT NULL,
    descripcion NVARCHAR(255),

    tabla_destino SYSNAME NOT NULL,
    modo_carga VARCHAR(10) NOT NULL, -- ADD | REPLACE
    sp_carga SYSNAME NOT NULL,

    activo BIT NOT NULL DEFAULT 1,
    fecha_creacion DATETIME2 DEFAULT SYSDATETIME(),

    CONSTRAINT fk_tema_area
        FOREIGN KEY (id_area) REFERENCES cat_area(id_area),

    CONSTRAINT chk_modo_carga
        CHECK (modo_carga IN ('ADD', 'REPLACE'))
);
--
--select * from cat_tema
insert into cat_tema(id_area, nombre,descripcion,tabla_destino,modo_carga,sp_carga ) 
	values(2,'Datos Generales','Número de personas derechohabientes adscritas a clínicas del IMSS',
	'pda_dg','REPLACE','sp_carga_pda_dg')
--

--cfg_diccionario_campo --> cat_diccionario_campo 
CREATE TABLE cat_diccionario_campo (
    id_campo INT IDENTITY PRIMARY KEY,
    id_tema INT NOT NULL,

    columna_excel NVARCHAR(100) NOT NULL,
    columna_bd SYSNAME NOT NULL,

    tipo_dato VARCHAR(50) NOT NULL,
    longitud INT NULL,
    obligatorio BIT NOT NULL DEFAULT 0,

    orden INT NOT NULL,
    activo BIT NOT NULL DEFAULT 1,

    CONSTRAINT fk_diccionario_tema
        FOREIGN KEY (id_tema) REFERENCES cat_tema(id_tema)
);
go
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'CVE_ENTIDAD','CVE_ENTIDAD', 'smallint',1)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, longitud, orden) values(1,'ENTIDAD','ENTIDAD', 'varchar', 255, 2)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'Periodo','Periodo', 'datetime',3)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'TOTAL PDA','TOTAL PDA', 'int',4)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'Titulares','Titulares', 'int',5)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'Puestos de trabajo','Puestos de trabajo', 'int',6)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'Pensionados','Pensionados', 'int',7)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'Conservación de derechos','Conservación de derechos', 'int',8)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'Sin empleo asociado','Sin empleo asociado', 'int',9)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'Estudiantes, Seguro Facultativo IMSS y CFE','Estudiantes, Seguro Facultativo IMSS y CFE', 'int',10)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'SS Familia','SS Familia', 'int',11)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'Continuación voluntaria','Continuación voluntaria', 'int',12)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'Familiares ','Familiares ', 'int',13)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'Esposa(o)/concubina(rio)','Esposa(o)/concubina(rio)', 'int',14)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'Hijas e hijos','Hijas e hijos', 'int',15)
INSERT into cat_diccionario_campo( id_tema, columna_excel, columna_bd, tipo_dato, orden) values(1,'EMadres y padres','Madres y padres', 'int',16)

	
CREATE TABLE log_carga (
    id_carga INT IDENTITY PRIMARY KEY,
    id_tema INT NOT NULL,
    usuario NVARCHAR(100) NOT NULL,

    nombre_archivo NVARCHAR(255),
    fecha_inicio DATETIME2 DEFAULT SYSDATETIME(),
    fecha_fin DATETIME2 NULL,

    registros_total INT DEFAULT 0,
    registros_ok INT DEFAULT 0,
    registros_error INT DEFAULT 0,

    estatus VARCHAR(20) NOT NULL, -- PENDIENTE | OK | ERROR
    mensaje NVARCHAR(MAX) NULL,

    CONSTRAINT fk_log_tema
        FOREIGN KEY (id_tema) REFERENCES cat_tema(id_tema)
);

--Tabla staging
CREATE TABLE stg_carga_generica (
    id_carga INT,
    fila INT,
    datos NVARCHAR(MAX), -- JSON
    error NVARCHAR(255)
);
