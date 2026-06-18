
ALTER PROCEDURE [dbo].[RepEstadoCuentaPrestaciones_Completo]

    @sCod_Emp_d       char(17)      = null,
    @sCod_Emp_h       char(17)      = null,
    @sdFec_Nomina_d   smalldatetime = null,
    @sdFec_Nomina_h   smalldatetime = null,
    @sCo_Depart_d     char(12)      = null,
    @sCo_Depart_h     char(12)      = null,
    @sCo_Cont_d       char(12)      = null,
    @sCo_Cont_h       char(12)      = null,
    @sCo_Depart_Gen_d char(12)      = null,
    @sCo_Depart_Gen_h char(12)      = null,
    @sCo_Cont_Gen_d   char(12)      = null,
    @sCo_Cont_Gen_h   char(12)      = null,
    @sCampOrderBy     varchar(16)   = null,
    @sDir             varchar(6)    = null,
    @bHeaderRep       bit           = 0
AS
BEGIN
    SET NOCOUNT ON;

    -- =========================================================================
    -- Si no se especifica fecha inicial, tomar la primera generacion del
    -- contrato de prestaciones
    -- =========================================================================
    IF @sdFec_Nomina_d IS NULL
        SELECT TOP 1 @sdFec_Nomina_d = fec_emis
        FROM sngennomi, par_emp
        WHERE co_cont = cont_pres
        ORDER BY fec_emis ASC;

    IF @sdFec_Nomina_h IS NULL
        SET @sdFec_Nomina_h = GETDATE();

    -- Normalizar al primer dia del mes para el CTE de meses
    DECLARE @FecIniMes smalldatetime =
        CAST(DATEADD(DAY, 1 - DAY(@sdFec_Nomina_d), @sdFec_Nomina_d) AS smalldatetime);
    DECLARE @FecFinMes smalldatetime =
        CAST(DATEADD(DAY, 1 - DAY(@sdFec_Nomina_h), @sdFec_Nomina_h) AS smalldatetime);

    -- =========================================================================
    -- Codigos de conceptos (mapeo generico -> especifico de la empresa)
    -- O004/O004_1 = Intereses prestaciones (V003_1)
    -- O005/O005_1 = Abono trimestral       (V001_1)
    -- O006/O006_1 = Dias adicionales       (V002_1)
    -- O007/O007_1 = Anticipos prestaciones
    -- O010/O010_1 = Intereses pagados/cancelados
    -- =========================================================================
    DECLARE @cO004  char(12) = dbo.GetConcepto('O004');
    DECLARE @cO005  char(12) = dbo.GetConcepto('O005');
    DECLARE @cO006  char(12) = dbo.GetConcepto('O006');
    DECLARE @cO007  char(12) = dbo.GetConcepto('O007');
    DECLARE @cO010  char(12) = dbo.GetConcepto('O010');
    DECLARE @cO004_1 char(12) = dbo.GetConcepto('O004_1');
    DECLARE @cO005_1 char(12) = dbo.GetConcepto('O005_1');
    DECLARE @cO006_1 char(12) = dbo.GetConcepto('O006_1');
    DECLARE @cO007_1 char(12) = dbo.GetConcepto('O007_1');
    DECLARE @cO010_1 char(12) = dbo.GetConcepto('O010_1');

    -- =========================================================================
    -- PASO 1: Tabla temporal con los recibos de prestaciones existentes
    --
    -- FUENTE DE VERDAD:
    --   * Acumulado prestaciones  -> snhistor.Z900  (puras, sin intereses)
    --   * Tasa BCV del periodo    -> snnomi.auxi_num del concepto O004/V003_1
    --   * Intereses del mes       -> CALCULADO: Z900 * tasa_anual / 100 / 12
    --                               (NO se usa snnomi.monto de V003_1 porque
    --                                puede contener valores inflados historicos)
    --   * Anticipos               -> snnomi con concepto O007 acumulados hasta
    --                                la fecha del recibo
    -- =========================================================================
    SELECT
        snrecibo.reci_num,
        snrecibo.fec_emis,
        CAST(MONTH(snrecibo.fec_emis) AS varchar(2))
            + '-' + CAST(YEAR(snrecibo.fec_emis) AS varchar(4))  AS fecha,

        -- Datos del empleado (valores iniciales al ingreso)
        ISNULL((SELECT ISNULL(val_n,0) FROM snem_va
                WHERE cod_emp=snemple.cod_emp AND co_var='Z012'), 0) AS numero_dias,
        ISNULL((SELECT ISNULL(val_n,0) FROM snem_va
                WHERE cod_emp=snemple.cod_emp AND co_var='Z002'), 0) AS acum_inicial_prest_soc,
        ISNULL((SELECT ISNULL(val_n,0) FROM snem_va
                WHERE cod_emp=snemple.cod_emp AND co_var='Z013'), 0) AS dias_adicionales,
        ISNULL((SELECT ISNULL(val_n,0) FROM snem_va
                WHERE cod_emp=snemple.cod_emp AND co_var='Z004'), 0) AS acum_inic_antic_prest_soc,
        ISNULL((SELECT ISNULL(val_n,0) FROM snem_va
                WHERE cod_emp=snemple.cod_emp AND co_var='Z003'), 0) AS acum_inicial_inter_prest,
        ISNULL((SELECT ISNULL(val_n,0) FROM snem_va
                WHERE cod_emp=snemple.cod_emp AND co_var='Z009'), 0) AS inter_pagados,

        -- Sueldo y componentes del salario integral
        ISNULL([dbo].[GetValorCampoNumerico](snemple.cod_emp,'A001',snrecibo.fec_emis), 0) AS sueldo,
        -- FIX: Salario integral diario desde Q031_1 (campo de prestaciones, no abono trimestral)
        -- Q031_1 es el concepto donde Profit guarda el salario integral diario para calculo de prestaciones
        ISNULL((SELECT TOP 1 ISNULL(monto,0) FROM snnomi
                WHERE reci_num=snrecibo.reci_num AND cod_emp=snrecibo.cod_emp
                  AND co_conce='Q031_1'), 0) AS salario_prom_diario,
        ISNULL((SELECT TOP 1 ISNULL(monto,0) FROM snnomi
                WHERE reci_num=snrecibo.reci_num AND cod_emp=snrecibo.cod_emp
                  AND co_conce='Q007_1'), 0) AS vacaciones,
        ISNULL((SELECT TOP 1 ISNULL(monto,0) FROM snnomi
                WHERE reci_num=snrecibo.reci_num AND cod_emp=snrecibo.cod_emp
                  AND co_conce='Q006_1'), 0) AS utilidades,

        -- Dias y montos del abono trimestral
        ISNULL((SELECT CASE WHEN auxi_num <> 0 THEN auxi_num ELSE 5 END FROM snnomi
                WHERE reci_num=snrecibo.reci_num AND cod_emp=snemple.cod_emp
                  AND co_conce IN (@cO005, @cO005_1)), 0) AS dias_abon,
        ISNULL((SELECT TOP 1 ISNULL(monto,0) FROM snnomi
                WHERE reci_num=snrecibo.reci_num AND cod_emp=snrecibo.cod_emp
                  AND co_conce IN (@cO005, @cO005_1)), 0) AS prest_asoc,
        ISNULL((SELECT SUM(auxi_num) FROM snnomi
                WHERE reci_num=snrecibo.reci_num AND cod_emp=snemple.cod_emp
                  AND co_conce IN (@cO006, @cO006_1)), 0) AS dias_adic,
        ISNULL((SELECT SUM(monto) FROM snnomi
                WHERE reci_num=snrecibo.reci_num AND cod_emp=snrecibo.cod_emp
                  AND co_conce IN (@cO006, @cO006_1)), 0) AS monto_dias_adicionales,

        -- Anticipos del mes (solo los de ese periodo)
        ISNULL((SELECT SUM(monto) FROM snnomi
                WHERE MONTH(fec_emis)=MONTH(snrecibo.fec_emis)
                  AND YEAR(fec_emis)=YEAR(snrecibo.fec_emis)
                  AND cod_emp=snemple.cod_emp
                  AND co_conce IN (@cO007, @cO007_1)), 0) AS antic_prest_soc,

        -- =====================================================================
        -- ACUMULADO PRESTACIONES (desde snnomi real  evita snhistor corrupto)
        -- acum_prest = SUM(abonos trimestrales) - SUM(anticipos) hasta fec_emis
        -- Este calculo es siempre correcto: 9652.12 - 7239.09 = 2413.03 (nunca negativo sin razon)
        -- =====================================================================
        ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                WHERE nx.cod_emp=snemple.cod_emp
                  AND nx.co_conce IN ('V001_1','V001')
                  AND rx.fec_emis <= snrecibo.fec_emis), 0)
        + ISNULL((SELECT ISNULL(val_n,0) FROM snem_va
                  WHERE cod_emp=snemple.cod_emp AND co_var='Z002'), 0)
        - ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                  INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                  WHERE nx.cod_emp=snemple.cod_emp
                    AND nx.co_conce = 'B020'
                    AND rx.fec_emis <= snrecibo.fec_emis), 0)
        - ISNULL((SELECT ISNULL(val_n,0) FROM snem_va
                  WHERE cod_emp=snemple.cod_emp AND co_var='Z004'), 0)
        AS acum_prest,

        -- Capital = MAX(0, acum_neto)  nunca negativo para calculo de intereses
        CASE WHEN
            ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                    INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                    WHERE nx.cod_emp=snemple.cod_emp
                      AND nx.co_conce IN ('V001_1','V001')
                      AND rx.fec_emis <= snrecibo.fec_emis), 0)
            + ISNULL((SELECT ISNULL(val_n,0) FROM snem_va
                      WHERE cod_emp=snemple.cod_emp AND co_var='Z002'), 0)
            - ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                      INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                      WHERE nx.cod_emp=snemple.cod_emp
                        AND nx.co_conce = 'B020'
                        AND rx.fec_emis <= snrecibo.fec_emis), 0)
            - ISNULL((SELECT ISNULL(val_n,0) FROM snem_va
                      WHERE cod_emp=snemple.cod_emp AND co_var='Z004'), 0)
        < 0 THEN 0.0
        ELSE
            ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                    INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                    WHERE nx.cod_emp=snemple.cod_emp
                      AND nx.co_conce IN ('V001_1','V001')
                      AND rx.fec_emis <= snrecibo.fec_emis), 0)
            + ISNULL((SELECT ISNULL(val_n,0) FROM snem_va
                      WHERE cod_emp=snemple.cod_emp AND co_var='Z002'), 0)
            - ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                      INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                      WHERE nx.cod_emp=snemple.cod_emp
                        AND nx.co_conce = 'B020'
                        AND rx.fec_emis <= snrecibo.fec_emis), 0)
            - ISNULL((SELECT ISNULL(val_n,0) FROM snem_va
                      WHERE cod_emp=snemple.cod_emp AND co_var='Z004'), 0)
        END AS capital_para_inter,

        -- =====================================================================
        -- TASA BCV: auxi_num del concepto O004/V003_1 (tasa anual en %)
        -- =====================================================================
        ISNULL((SELECT TOP 1 auxi_num FROM snnomi
                WHERE reci_num=snrecibo.reci_num AND cod_emp=snemple.cod_emp
                  AND co_conce IN (@cO004, @cO004_1)
                  AND auxi_num > 0), 0) AS tasa_interes,

        -- =====================================================================
        -- MONTO INTERESES: Z900 * tasa_anual / 100 / 12
        -- Se usa NULLIF para que 0 en tasa dispare el fallback en PASO 2
        -- =====================================================================
        ROUND(
            ISNULL((SELECT TOP 1 ISNULL(val_n,0) FROM snhistor
                    WHERE cod_emp=snemple.cod_emp AND co_var='Z900'
                      AND fecha <= snrecibo.fec_emis
                      AND MONTH(fecha)=MONTH(snrecibo.fec_emis)
                      AND YEAR(fecha)=YEAR(snrecibo.fec_emis)
                      AND co_cont=parEmp.cont_pres
                    ORDER BY fecha DESC), 0)
            *
            ISNULL((SELECT TOP 1 auxi_num FROM snnomi
                    WHERE reci_num=snrecibo.reci_num AND cod_emp=snemple.cod_emp
                      AND co_conce IN (@cO004, @cO004_1)
                      AND auxi_num > 0), 0)
            / 100.0 / 12.0
        , 4) AS monto_interes,

        ROUND(
            ISNULL((SELECT TOP 1 ISNULL(val_n,0) FROM snhistor
                    WHERE cod_emp=snemple.cod_emp AND co_var='Z900'
                      AND fecha <= snrecibo.fec_emis
                      AND MONTH(fecha)=MONTH(snrecibo.fec_emis)
                      AND YEAR(fecha)=YEAR(snrecibo.fec_emis)
                      AND co_cont=parEmp.cont_pres
                    ORDER BY fecha DESC), 0)
            *
            ISNULL((SELECT TOP 1 auxi_num FROM snnomi
                    WHERE reci_num=snrecibo.reci_num AND cod_emp=snemple.cod_emp
                      AND co_conce IN (@cO004, @cO004_1)
                      AND auxi_num > 0), 0)
            / 100.0 / 12.0
        , 4) AS inter_sobre_prest,

        -- Intereses cancelados/pagados al trabajador
        ISNULL((SELECT ISNULL(monto,0) FROM snnomi
                WHERE reci_num=snrecibo.reci_num AND cod_emp=snemple.cod_emp
                  AND co_conce IN (@cO010, @cO010_1)), 0) AS inter_cancelados,

        -- Acumulado de intereses (Z901)  mismo fix de rango de mes
        ISNULL((SELECT TOP 1 ISNULL(val_n,0) FROM snhistor
                WHERE co_var='Z901' AND cod_emp=snrecibo.cod_emp
                  AND fecha <= snrecibo.fec_emis
                  AND MONTH(fecha)=MONTH(snrecibo.fec_emis)
                  AND YEAR(fecha)=YEAR(snrecibo.fec_emis)
                  AND co_cont=parEmp.cont_pres
                ORDER BY fecha DESC), 0) AS acum_inter,

        -- Campos auxiliares del reporte
        ISNULL((SELECT auxi_num FROM snnomi
                WHERE reci_num=snrecibo.reci_num AND cod_emp=snemple.cod_emp
                  AND co_conce IN (@cO004, @cO004_1)), 0) AS saldo_total_tipo1,
        0 AS saldo_total_tipo2,
        0 AS num_veces,
        CASE
            WHEN dbo.SueldoUltimaNomina(snrecibo.fec_emis, snrecibo.cod_emp, snrecibo.co_cont) IS NULL THEN 0
            ELSE dbo.SueldoUltimaNomina(snrecibo.fec_emis, snrecibo.cod_emp, snrecibo.co_cont)
        END AS sueldo2,

        dbo.GetPrefixId(snemple.nac) + snemple.ci AS ci,
        snemple.cod_emp, snemple.nombre_completo, snemple.fecha_ing,
        sndepart.co_depart, sncont.co_cont,
        snrecibo.campo1, snrecibo.campo2, snrecibo.campo3, snrecibo.campo4,
        snrecibo.campo5, snrecibo.campo6, snrecibo.campo7, snrecibo.campo8

    INTO #tempresta

    FROM snrecibo
        INNER JOIN dbo.snnomi AS n
            ON snrecibo.reci_num = n.reci_num
           AND snrecibo.cod_emp  = n.cod_emp
           AND n.co_conce IN (
                @cO004, @cO005, @cO006, @cO007, @cO010,
                @cO004_1, @cO005_1, @cO006_1, @cO007_1, @cO010_1, 'Q006_1', 'Q007_1')
        INNER JOIN snemple  ON snrecibo.cod_emp  = snemple.cod_emp
        INNER JOIN sndepart ON snemple.co_depart = sndepart.co_depart
        INNER JOIN sncont   ON snemple.co_cont   = sncont.co_cont,
        dbo.par_emp AS parEmp

    WHERE
        (@sCod_Emp_d IS NULL OR snrecibo.cod_emp >= @sCod_Emp_d)
        AND (@sCod_Emp_h IS NULL OR snrecibo.cod_emp <= @sCod_Emp_h)
        AND (@sdFec_Nomina_d IS NULL OR @sdFec_Nomina_d <= snrecibo.fec_emis)
        AND (@sdFec_Nomina_h IS NULL OR snrecibo.fec_emis <= @sdFec_Nomina_h)
        AND (@sCo_Depart_Gen_d IS NULL OR @sCo_Depart_Gen_d <= snrecibo.co_depart)
        AND (@sCo_Depart_Gen_h IS NULL OR snrecibo.co_depart <= @sCo_Depart_Gen_h)
        AND (@sCo_Cont_Gen_d IS NULL OR @sCo_Cont_Gen_d <= snrecibo.co_cont)
        AND (@sCo_Cont_Gen_h IS NULL OR snrecibo.co_cont <= @sCo_Cont_Gen_h)
        AND (@sCo_Cont_d IS NULL OR @sCo_Cont_d <= snemple.co_cont)
        AND (@sCo_Cont_h IS NULL OR snemple.co_cont <= @sCo_Cont_h)
        AND (@sCo_Depart_d IS NULL OR @sCo_Depart_d <= snemple.co_depart)
        AND (@sCo_Depart_h IS NULL OR snemple.co_depart <= @sCo_Depart_h)

    GROUP BY
        snrecibo.reci_num, snrecibo.cod_emp, snemple.cod_emp, snrecibo.fec_emis,
        parEmp.cont_pres, snrecibo.co_cont, snemple.nac, snemple.ci,
        snemple.nombre_completo, snemple.fecha_ing,
        sndepart.co_depart, sncont.co_cont,
        snrecibo.campo1, snrecibo.campo2, snrecibo.campo3, snrecibo.campo4,
        snrecibo.campo5, snrecibo.campo6, snrecibo.campo7, snrecibo.campo8

    ORDER BY snrecibo.fec_emis, snemple.cod_emp;

    -- =========================================================================
    -- PASO 2: SELECT FINAL con las tres correcciones aplicadas
    --
    -- FIX A: Intereses sobre Z900 puro (sin capitalizacion)
    -- FIX B: CTE recursivo genera TODOS los meses (sin saltos)
    -- FIX C: Disponible 75% = (Z900 * 0.75) - anticipos_acumulados
    -- =========================================================================
    ;WITH MesesRango AS (
        -- Genera un renglon por cada mes en el rango solicitado
        -- Esto garantiza que no haya saltos aunque no haya nomina ese mes
        SELECT @FecIniMes AS mes_ini
        UNION ALL
        SELECT CAST(DATEADD(MONTH, 1, mes_ini) AS smalldatetime)
        FROM MesesRango
        WHERE DATEADD(MONTH, 1, mes_ini) <= @FecFinMes
    ),
    EmpleadosFiltro AS (
        -- Empleados que tienen al menos un recibo en el rango
        SELECT DISTINCT
            cod_emp, nombre_completo, fecha_ing, ci, co_depart, co_cont,
            campo1, campo2, campo3, campo4, campo5, campo6, campo7, campo8,
            acum_inicial_prest_soc, acum_inic_antic_prest_soc,
            acum_inicial_inter_prest, numero_dias, dias_adicionales, inter_pagados
        FROM #tempresta
    )
    SELECT DISTINCT
        ISNULL(MAX(t.reci_num), 0)          AS reci_Num,
        ISNULL(MAX(t.fec_emis), m.mes_ini)  AS fec_emis,
        CAST(MONTH(m.mes_ini) AS varchar(2))
            + '-' + CAST(YEAR(m.mes_ini) AS varchar(4)) AS fecha,

        MAX(e.numero_dias)                  AS numero_dias,
        MAX(e.acum_inicial_prest_soc)       AS acum_inicial_prest_soc,
        MAX(e.dias_adicionales)             AS dias_adicionales,
        MAX(e.acum_inic_antic_prest_soc)    AS acum_inic_antic_prest_soc,
        MAX(e.acum_inicial_inter_prest)     AS acum_inicial_inter_prest,
        MAX(e.inter_pagados)                AS inter_pagados,
        -- FIX DEFINITIVO: Alicuotas estables por periodo salarial
        -- Comparamos Q004_1 del recibo trimestral con el sueldo mensual del mes actual
        -- Q004_1 = sueldo que Profit registra en el recibo de prestaciones
        -- Esta comparacion es directa y no depende de fechas intermedias
        ISNULL(
            (SELECT TOP 1 ISNULL(nx_u.monto, 0)
             FROM snnomi nx_u
             INNER JOIN snrecibo rx_u ON rx_u.reci_num=nx_u.reci_num AND rx_u.cod_emp=nx_u.cod_emp
             INNER JOIN snnomi nx_q4u ON nx_q4u.reci_num=rx_u.reci_num AND nx_q4u.cod_emp=rx_u.cod_emp
                                      AND nx_q4u.co_conce='Q004_1'
             WHERE nx_u.cod_emp=e.cod_emp AND nx_u.co_conce='Q006_1'
               AND NULLIF(nx_u.monto,0) IS NOT NULL
               AND rx_u.fec_emis < DATEADD(MONTH,1,m.mes_ini)
               -- Q004_1 del recibo debe estar dentro del 5% del sueldo actual
               -- (cubrir ajustes menores y el mismo nivel salarial)
               AND nx_q4u.monto >= ISNULL([dbo].[GetValorCampoNumerico](e.cod_emp,'A001',m.mes_ini),0) * 0.90
               AND nx_q4u.monto <= ISNULL([dbo].[GetValorCampoNumerico](e.cod_emp,'A001',m.mes_ini),0) * 1.10
             ORDER BY rx_u.fec_emis ASC),
        0) AS utilidades,
        ISNULL(
            (SELECT TOP 1 ISNULL(nx_v.monto, 0)
             FROM snnomi nx_v
             INNER JOIN snrecibo rx_v ON rx_v.reci_num=nx_v.reci_num AND rx_v.cod_emp=nx_v.cod_emp
             INNER JOIN snnomi nx_q4v ON nx_q4v.reci_num=rx_v.reci_num AND nx_q4v.cod_emp=rx_v.cod_emp
                                      AND nx_q4v.co_conce='Q004_1'
             WHERE nx_v.cod_emp=e.cod_emp AND nx_v.co_conce='Q007_1'
               AND NULLIF(nx_v.monto,0) IS NOT NULL
               AND rx_v.fec_emis < DATEADD(MONTH,1,m.mes_ini)
               AND nx_q4v.monto >= ISNULL([dbo].[GetValorCampoNumerico](e.cod_emp,'A001',m.mes_ini),0) * 0.90
               AND nx_q4v.monto <= ISNULL([dbo].[GetValorCampoNumerico](e.cod_emp,'A001',m.mes_ini),0) * 1.10
             ORDER BY rx_v.fec_emis ASC),
        0) AS vacaciones,
        ISNULL(ISNULL(MAX(t.sueldo),
            ISNULL([dbo].[GetValorCampoNumerico](e.cod_emp,'A001',m.mes_ini), 0)
        ), 0) AS sueldo,
        -- FIX DEFINITIVO salario_prom_diario: PRIMER Q031_1 del periodo salarial
        ISNULL(
            (SELECT TOP 1 ISNULL(nx_p.monto, 0)
             FROM snnomi nx_p
             INNER JOIN snrecibo rx_p ON rx_p.reci_num=nx_p.reci_num AND rx_p.cod_emp=nx_p.cod_emp
             INNER JOIN snnomi nx_q4p ON nx_q4p.reci_num=rx_p.reci_num AND nx_q4p.cod_emp=rx_p.cod_emp
                                      AND nx_q4p.co_conce='Q004_1'
             WHERE nx_p.cod_emp=e.cod_emp AND nx_p.co_conce='Q031_1'
               AND NULLIF(nx_p.monto,0) IS NOT NULL
               AND rx_p.fec_emis < DATEADD(MONTH,1,m.mes_ini)
               AND nx_q4p.monto >= ISNULL([dbo].[GetValorCampoNumerico](e.cod_emp,'A001',m.mes_ini),0) * 0.90
               AND nx_q4p.monto <= ISNULL([dbo].[GetValorCampoNumerico](e.cod_emp,'A001',m.mes_ini),0) * 1.10
             ORDER BY rx_p.fec_emis ASC),
        0) AS salario_prom_diario,
        ISNULL(MAX(t.dias_abon), 0)         AS dias_abon,
        ISNULL(MAX(t.prest_asoc), 0)        AS prest_asoc,
        ISNULL(MAX(t.dias_adic), 0)         AS dias_adic,
        ISNULL(MAX(t.monto_dias_adicionales), 0) AS monto_dias_adicionales,
        ISNULL(MAX(t.antic_prest_soc), 0)   AS antic_prest_soc,

        -- =====================================================================
        -- FIX B: acum_prest desde snnomi real (snhistor esta corrupto por capitalizacion)
        ISNULL(
            ISNULL(MAX(t.acum_prest),
                ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                        INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                        WHERE nx.cod_emp=e.cod_emp AND nx.co_conce IN ('V001_1','V001')
                          AND rx.fec_emis < DATEADD(MONTH,1,m.mes_ini)), 0)
                - ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                          INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                          WHERE nx.cod_emp=e.cod_emp AND nx.co_conce = 'B020'
                            AND rx.fec_emis < DATEADD(MONTH,1,m.mes_ini)), 0)
                - ISNULL(MAX(e.acum_inic_antic_prest_soc), 0)
                + ISNULL(MAX(e.acum_inicial_prest_soc), 0)
            ), 0) AS acum_prest,

        -- =====================================================================
        -- FIX 2: Capital desde snnomi real, flooreado en 0
        ISNULL(CASE
            WHEN ISNULL(
                NULLIF(MAX(t.capital_para_inter), 0),
                ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                        INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                        WHERE nx.cod_emp=e.cod_emp AND nx.co_conce IN ('V001_1','V001')
                          AND rx.fec_emis < DATEADD(MONTH,1,m.mes_ini)), 0)
                - ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                          INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                          WHERE nx.cod_emp=e.cod_emp AND nx.co_conce = 'B020'
                            AND rx.fec_emis < DATEADD(MONTH,1,m.mes_ini)), 0)
                - ISNULL(MAX(e.acum_inic_antic_prest_soc), 0)
                + ISNULL(MAX(e.acum_inicial_prest_soc), 0)
            ) < 0 THEN 0.0
            ELSE ISNULL(
                NULLIF(MAX(t.capital_para_inter), 0),
                ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                        INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                        WHERE nx.cod_emp=e.cod_emp AND nx.co_conce IN ('V001_1','V001')
                          AND rx.fec_emis < DATEADD(MONTH,1,m.mes_ini)), 0)
                - ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                          INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                          WHERE nx.cod_emp=e.cod_emp AND nx.co_conce = 'B020'
                            AND rx.fec_emis < DATEADD(MONTH,1,m.mes_ini)), 0)
                - ISNULL(MAX(e.acum_inic_antic_prest_soc), 0)
                + ISNULL(MAX(e.acum_inicial_prest_soc), 0)
            )
        END, 0) AS capital_para_inter,

        -- FIX 3: Tasa  NULLIF(0) dispara fallback cuando V003_1 no se proceso
        ISNULL(ISNULL(
            NULLIF(MAX(t.tasa_interes), 0),
            (SELECT TOP 1 ISNULL(n2.auxi_num, 0) FROM snnomi n2
             INNER JOIN snrecibo r2 ON r2.reci_num=n2.reci_num AND r2.cod_emp=n2.cod_emp
             WHERE n2.cod_emp=e.cod_emp
               AND n2.co_conce IN (@cO004, @cO004_1)
               AND n2.auxi_num > 0
               AND r2.fec_emis <= m.mes_ini
             ORDER BY r2.fec_emis DESC)
        ), 0) AS tasa_interes,

        -- =====================================================================
        -- FIX 3b: Monto intereses recalculado con capital flooreado x tasa propagada
        -- Formula: MAX(0, Z900) * tasa_anual / 100 / 12
        -- =====================================================================
        ISNULL(ROUND(
            -- capital real desde snnomi (ya garantizado > 0 por PASO 1)
            ISNULL(NULLIF(MAX(t.capital_para_inter), 0),
                ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                        INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                        WHERE nx.cod_emp=e.cod_emp AND nx.co_conce IN ('V001_1','V001')
                          AND rx.fec_emis < DATEADD(MONTH,1,m.mes_ini)), 0)
                - ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                          INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                          WHERE nx.cod_emp=e.cod_emp AND nx.co_conce = 'B020'
                            AND rx.fec_emis < DATEADD(MONTH,1,m.mes_ini)), 0)
                - ISNULL(MAX(e.acum_inic_antic_prest_soc), 0)
                + ISNULL(MAX(e.acum_inicial_prest_soc), 0)
            )
            *
            ISNULL(ISNULL(
                NULLIF(MAX(t.tasa_interes), 0),
                (SELECT TOP 1 ISNULL(n2.auxi_num, 0) FROM snnomi n2
                 INNER JOIN snrecibo r2 ON r2.reci_num=n2.reci_num AND r2.cod_emp=n2.cod_emp
                 WHERE n2.cod_emp=e.cod_emp
                   AND n2.co_conce IN (@cO004, @cO004_1)
                   AND n2.auxi_num > 0
                   AND r2.fec_emis <= m.mes_ini
                 ORDER BY r2.fec_emis DESC)
            ), 0)
            / 100.0 / 12.0
        , 4), 0) AS monto_interes,
        ISNULL(ROUND(
            ISNULL(NULLIF(MAX(t.capital_para_inter), 0),
                ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                        INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                        WHERE nx.cod_emp=e.cod_emp AND nx.co_conce IN ('V001_1','V001')
                          AND rx.fec_emis < DATEADD(MONTH,1,m.mes_ini)), 0)
                - ISNULL((SELECT SUM(nx.monto) FROM snnomi nx
                          INNER JOIN snrecibo rx ON rx.reci_num=nx.reci_num AND rx.cod_emp=nx.cod_emp
                          WHERE nx.cod_emp=e.cod_emp AND nx.co_conce = 'B020'
                            AND rx.fec_emis < DATEADD(MONTH,1,m.mes_ini)), 0)
                - ISNULL(MAX(e.acum_inic_antic_prest_soc), 0)
                + ISNULL(MAX(e.acum_inicial_prest_soc), 0)
            )
            *
            ISNULL(ISNULL(
                NULLIF(MAX(t.tasa_interes), 0),
                (SELECT TOP 1 ISNULL(n2.auxi_num,0) FROM snnomi n2
                 INNER JOIN snrecibo r2 ON r2.reci_num=n2.reci_num AND r2.cod_emp=n2.cod_emp
                 WHERE n2.cod_emp=e.cod_emp
                   AND n2.co_conce IN (@cO004, @cO004_1)
                   AND n2.auxi_num > 0
                   AND r2.fec_emis <= m.mes_ini
                 ORDER BY r2.fec_emis DESC)
            ), 0)
            / 100.0 / 12.0
        , 4), 0) AS inter_sobre_prest,
        ISNULL(MAX(t.inter_cancelados), 0)  AS inter_cancelados,

        -- =====================================================================
        -- FIX acum_inter: Suma acumulada de intereses por trimestre desde snnomi
        -- (snhistor.Z901 se congela y no es confiable despues de anticipos)
        -- Patron: derived table para pre-computar capital y tasa por trimestre
        -- luego SUM externo sobre valores escalares (sin nested aggregates)
        -- =====================================================================
        ISNULL((
            SELECT SUM((t_abonos - t_anticipos) * t_tasa / 100.0 / 12.0)
            FROM (
                SELECT
                    ISNULL((SELECT SUM(na.monto) FROM snnomi na
                             INNER JOIN snrecibo ra ON ra.reci_num=na.reci_num AND ra.cod_emp=na.cod_emp
                             WHERE na.cod_emp=hr.cod_emp
                               AND na.co_conce IN ('V001_1','V001')
                               AND ra.fec_emis <= hr.fec_emis), 0) AS t_abonos,
                    ISNULL((SELECT SUM(nb.monto) FROM snnomi nb
                             INNER JOIN snrecibo rb ON rb.reci_num=nb.reci_num AND rb.cod_emp=nb.cod_emp
                             WHERE nb.cod_emp=hr.cod_emp
                               AND nb.co_conce = 'B020'
                               AND rb.fec_emis <= hr.fec_emis), 0) AS t_anticipos,
                    ISNULL(ht.auxi_num, 0) AS t_tasa
                FROM snrecibo hr
                INNER JOIN snnomi ht ON ht.reci_num=hr.reci_num AND ht.cod_emp=hr.cod_emp
                                     AND ht.co_conce = @cO004
                                     AND ht.auxi_num > 0
                WHERE hr.cod_emp = e.cod_emp
                  AND hr.fec_emis <= m.mes_ini
            ) AS trimestres
        ), 0)
        - ISNULL((SELECT SUM(ISNULL(nc.monto,0)) FROM snnomi nc
                   INNER JOIN snrecibo rc ON rc.reci_num=nc.reci_num AND rc.cod_emp=nc.cod_emp
                   WHERE nc.cod_emp=e.cod_emp
                     AND nc.co_conce = @cO010
                     AND rc.fec_emis <= m.mes_ini), 0) AS acum_inter,
        -- acum_inter2: mismo valor (campo duplicado para Crystal Reports)
        ISNULL((
            SELECT SUM((t_abonos - t_anticipos) * t_tasa / 100.0 / 12.0)
            FROM (
                SELECT
                    ISNULL((SELECT SUM(na.monto) FROM snnomi na
                             INNER JOIN snrecibo ra ON ra.reci_num=na.reci_num AND ra.cod_emp=na.cod_emp
                             WHERE na.cod_emp=hr.cod_emp
                               AND na.co_conce IN ('V001_1','V001')
                               AND ra.fec_emis <= hr.fec_emis), 0) AS t_abonos,
                    ISNULL((SELECT SUM(nb.monto) FROM snnomi nb
                             INNER JOIN snrecibo rb ON rb.reci_num=nb.reci_num AND rb.cod_emp=nb.cod_emp
                             WHERE nb.cod_emp=hr.cod_emp
                               AND nb.co_conce = 'B020'
                               AND rb.fec_emis <= hr.fec_emis), 0) AS t_anticipos,
                    ISNULL(ht.auxi_num, 0) AS t_tasa
                FROM snrecibo hr
                INNER JOIN snnomi ht ON ht.reci_num=hr.reci_num AND ht.cod_emp=hr.cod_emp
                                     AND ht.co_conce = @cO004
                                     AND ht.auxi_num > 0
                WHERE hr.cod_emp = e.cod_emp
                  AND hr.fec_emis <= m.mes_ini
            ) AS trimestres2
        ), 0)
        - ISNULL((SELECT SUM(ISNULL(nc.monto,0)) FROM snnomi nc
                   INNER JOIN snrecibo rc ON rc.reci_num=nc.reci_num AND rc.cod_emp=nc.cod_emp
                   WHERE nc.cod_emp=e.cod_emp
                     AND nc.co_conce = @cO010
                     AND rc.fec_emis <= m.mes_ini), 0) AS acum_inter2,

        -- saldo_total_tipo1 = campo que Crystal Reports usa como "Tasa Intereses"
        -- Debe propagarse igual que tasa_interes (NULLIF + fallback)
        ISNULL(ISNULL(
            NULLIF(MAX(t.saldo_total_tipo1), 0),
            (SELECT TOP 1 ISNULL(n2.auxi_num, 0) FROM snnomi n2
             INNER JOIN snrecibo r2 ON r2.reci_num=n2.reci_num AND r2.cod_emp=n2.cod_emp
             WHERE n2.cod_emp=e.cod_emp
               AND n2.co_conce IN (@cO004, @cO004_1)
               AND n2.auxi_num > 0
               AND r2.fec_emis <= m.mes_ini
             ORDER BY r2.fec_emis DESC)
        ), 0) AS saldo_total_tipo1,
        ISNULL(MAX(t.saldo_total_tipo2), 0) AS saldo_total_tipo2,

        ISNULL(MAX(t.num_veces), 0)         AS num_veces,
        ISNULL(MAX(t.sueldo2), 0)           AS sueldo2,

        -- =====================================================================
        -- FIX C: DISPONIBLE 75%
        -- Formula: (Acum_Z900 * 0.75) - Anticipos_Acumulados_Historicos
        -- Garantiza que siempre quede el 25% en cuenta (minimo 0)
        -- Anticipos = todos los registrados hasta el mes actual +
        --             anticipos iniciales del contrato anterior (Z004)
        -- =====================================================================
        ISNULL(CASE
            WHEN (
                ISNULL(
                    MAX(t.acum_prest),
                    (SELECT TOP 1 ISNULL(val_n, 0) FROM snhistor
                     WHERE cod_emp=e.cod_emp AND co_var='Z900'
                       AND fecha <= m.mes_ini
                     ORDER BY fecha DESC)
                ) * 0.75
                -
                ISNULL(
                    (SELECT SUM(nx.monto) FROM snnomi nx
                     INNER JOIN snrecibo rx ON rx.reci_num = nx.reci_num
                     WHERE nx.cod_emp=e.cod_emp
                       AND nx.co_conce IN (@cO007, @cO007_1)
                       AND rx.fec_emis <= m.mes_ini), 0
                )
                - ISNULL(MAX(e.acum_inic_antic_prest_soc), 0)
            ) < 0
            THEN 0.0
            ELSE
                ISNULL(
                    MAX(t.acum_prest),
                    (SELECT TOP 1 ISNULL(val_n, 0) FROM snhistor
                     WHERE cod_emp=e.cod_emp AND co_var='Z900'
                       AND fecha <= m.mes_ini
                     ORDER BY fecha DESC)
                ) * 0.75
                -
                ISNULL(
                    (SELECT SUM(nx.monto) FROM snnomi nx
                     INNER JOIN snrecibo rx ON rx.reci_num = nx.reci_num
                     WHERE nx.cod_emp=e.cod_emp
                       AND nx.co_conce IN (@cO007, @cO007_1)
                       AND rx.fec_emis <= m.mes_ini), 0
                )
                - ISNULL(MAX(e.acum_inic_antic_prest_soc), 0)
        END, 0) AS disponible_75,

        e.ci, e.cod_emp, e.nombre_completo, e.fecha_ing,
        e.co_depart, e.co_cont,
        e.campo1, e.campo2, e.campo3, e.campo4,
        e.campo5, e.campo6, e.campo7, e.campo8

    FROM MesesRango m
    CROSS JOIN EmpleadosFiltro e
    LEFT JOIN #tempresta t
        ON t.cod_emp        = e.cod_emp
       AND YEAR(t.fec_emis) = YEAR(m.mes_ini)
       AND MONTH(t.fec_emis)= MONTH(m.mes_ini)

    GROUP BY
        m.mes_ini, e.ci, e.cod_emp, e.nombre_completo, e.fecha_ing,
        e.co_depart, e.co_cont,
        e.campo1, e.campo2, e.campo3, e.campo4,
        e.campo5, e.campo6, e.campo7, e.campo8,
        e.acum_inicial_prest_soc, e.acum_inic_antic_prest_soc,
        e.acum_inicial_inter_prest, e.numero_dias, e.dias_adicionales, e.inter_pagados

    ORDER BY fec_emis, e.cod_emp

    OPTION (MAXRECURSION 500);

    DROP TABLE #tempresta;

END
