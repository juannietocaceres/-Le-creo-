CREATE TABLE IF NOT EXISTS canales_oficiales (
  id            SERIAL PRIMARY KEY,
  entidad       TEXT NOT NULL,
  sector        TEXT NOT NULL,          -- banco, billetera, mensajeria, gobierno, otro
  canales       TEXT NOT NULL,          -- cómo contacta de verdad
  nunca_pide    TEXT NOT NULL,          -- lo que la entidad nunca pide
  fuente_url    TEXT NOT NULL,          -- página oficial donde se verificó
  verificado_en DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS dominios_oficiales (
  dominio  TEXT PRIMARY KEY,            -- ej: bancolombia.com
  entidad  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS acortadores (
  dominio TEXT PRIMARY KEY              -- ej: bit.ly
);

CREATE TABLE IF NOT EXISTS numeros_reportados (
  numero          TEXT PRIMARY KEY,     -- formato +57XXXXXXXXXX
  reportes        INT  NOT NULL DEFAULT 0,
  ultimo_reporte  DATE,
  origen          TEXT NOT NULL         -- semilla_ficticia | usuario
);

CREATE TABLE IF NOT EXISTS analisis (   -- SIN texto original (decisión 6)
  id           SERIAL PRIMARY KEY,
  fecha        TIMESTAMPTZ DEFAULT now(),
  tipo_entrada TEXT,                    -- texto | imagen | audio
  semaforo     TEXT,                    -- rojo | amarillo | verde | rechazo | error
  senales      JSONB,
  proveedor    TEXT,
  modelo       TEXT,
  tokens_in    INT,
  tokens_out   INT,
  latencia_ms  INT,
  iteraciones  INT,
  ok           BOOLEAN
);

CREATE TABLE IF NOT EXISTS feedback (   -- F2: el usuario corrige
  id          SERIAL PRIMARY KEY,
  analisis_id INT REFERENCES analisis(id),
  usuario_dice TEXT,                    -- "era_estafa" | "no_era_estafa"
  fecha       TIMESTAMPTZ DEFAULT now()
);
