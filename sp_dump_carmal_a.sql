
------------------------------------------------------------------
-- Versión: Base Imponible Exenta (tipo_imp = 5)
-- Fecha: 05/03/2026
------------------------------------------------------------------
CREATE PROCEDURE [dbo].[RepFormatoFacturaVentaOM_Consolidada]
    @cCo_Numero_d CHAR(20) = NULL,
    @cCo_Numero_h CHAR(20) = NULL ,
    @cCo_Sucursal CHAR(6) = NULL ,
    @sCampOrderBy VARCHAR(16) = NULL ,
    @sDir VARCHAR(6) = NULL ,
    @bHeaderRep BIT = 0
AS 
    BEGIN
        SET NOCOUNT ON ;

        DECLARE @Direc VARCHAR(1000), @Telef VARCHAR(100), @Email VARCHAR(100) ;
        SELECT @Direc = val_str FROM saAdiCampo WHERE co_adicampo='DIR_FIS';
        SELECT @Telef = val_str FROM saAdiCampo WHERE co_adicampo='TELEF';
        SELECT @Email = val_str FROM saAdiCampo WHERE co_adicampo='EMAIL';

        DECLARE @Tipo_doc CHAR(11);
        SET @Tipo_doc = 'factventa' ;

        SELECT
            @Direc AS DIRECCION_EMP
            , @Telef AS TELEFONO_EMP
            , @Email AS CORREO_EMP
            , CL.cli_des
            , CL.ciudad AS NComercial
            , CL.nit AS SICA
            , CL.campo1, CL.campo2, CL.campo3, CL.campo4, CL.campo5, CL.campo6, CL.campo7, CL.campo8
            , CL.rif, CL.nit, CL.telefonos
            , FV.campo2 AS fax
            , CL.direc1
            , FV.campo4 AS FechaCONT
            , (CASE WHEN (FV.dir_ent IS NOT NULL AND len(ltrim(FV.dir_ent)) > 0) THEN FV.dir_ent ELSE CL.dir_ent2 END) AS dir_entrega
            , VE.ven_des
            , TR.des_tran
            , CP.cond_des
            , MO.mone_des
            , FV.doc_num, FV.descrip, FV.co_cli, FV.co_tran, FV.co_mone, FV.co_ven, FV.co_cond
            , FV.fec_emis, FV.fec_venc, FV.fec_reg, FV.anulado, FV.status, FV.n_control, FV.ven_ter
            , FV.tasa
            , ISNULL(FV.porc_desc_glob, '0') AS porc_desc_glob
            
            -- CABECERA EN BS
            , AVG(FV.monto_desc_glob) AS monto_desc_glob
            , AVG(FV.monto_reca) AS monto_reca
            , AVG(FV.total_bruto) AS total_bruto
            , AVG(FV.monto_imp) AS monto_imp
            , AVG(FV.total_neto) AS total_neto
            , AVG(FV.saldo) AS saldo

            -- CABECERA EN USD
            , AVG(FV.monto_desc_glob / NULLIF(FV.tasa, 0)) AS monto_desc_glob2
            , AVG(FV.monto_reca / NULLIF(FV.tasa, 0)) AS monto_reca2
            , AVG(FV.total_bruto / NULLIF(FV.tasa, 0)) AS total_bruto2
            , AVG(FV.monto_imp / NULLIF(FV.tasa, 0)) AS monto_imp2
            , AVG(FV.monto_imp2 / NULLIF(FV.tasa, 0)) AS monto_imp22
            , AVG(FV.monto_imp3 / NULLIF(FV.tasa, 0)) AS monto_imp3
            , AVG(FV.otros1 / NULLIF(FV.tasa, 0)) AS otros1
            , AVG(FV.otros2 / NULLIF(FV.tasa, 0)) AS otros2
            , AVG(FV.otros3 / NULLIF(FV.tasa, 0)) AS otros3
            , AVG(FV.total_neto / NULLIF(FV.tasa, 0)) AS total_neto2
            
            , FV.dir_ent
            , FV.comentario
            , ROW_NUMBER() OVER(ORDER BY FVR.co_art ASC) AS reng_num
            , FVR.co_art
            , ART.art_des
            , SUM(CASE WHEN FVR.co_uni = 'UNI' THEN FVR.total_art ELSE 
                CASE WHEN UNI.relacion = 0 THEN (FVR.total_art * UNI.equivalencia) ELSE (FVR.total_art / UNI.equivalencia) END 
              END) AS total_art
            , UNI.equivalencia
            , SUM(ART.stock_pedido) AS peso
            , FVR.co_alma
            , SUM(FVR.stotal_art) AS stotal_art
            , FVR.co_uni, FVR.sco_uni, FVR.co_precio
            
            -- RENGLONES
            , FVR.prec_vta AS prec_vta
            , (FVR.prec_vta / NULLIF(FV.tasa, 0)) AS prec_vta2
            , FVR.prec_vta_om AS prec_vta_om
            , ISNULL(FVR.porc_desc, 0) AS porc_desc
            , SUM(FVR.monto_desc) AS monto_desc
            , SUM(FVR.monto_desc / NULLIF(FV.tasa, 0)) AS monto_desc2
            , FVR.tipo_imp, FVR.tipo_imp2, FVR.tipo_imp3, FVR.porc_imp, FVR.porc_imp2, FVR.porc_imp3
            
            -- Impuestos Reales
            , SUM(FVR.monto_imp) AS reng_monto_imp
            , SUM(FVR.monto_imp / NULLIF(FV.tasa, 0)) AS reng_monto_imp2
            , SUM(FVR.monto_imp2 / NULLIF(FV.tasa, 0)) AS reng_monto_imp22
            , SUM(FVR.monto_imp3 / NULLIF(FV.tasa, 0)) AS reng_monto_imp3

            ---------------------------------------------------------
            -- NUEVOS CAMPOS: VALOR BRUTO EXENTO (tipo_imp = 5)
            -- Cálculo: Precio * Cantidad (Sin impuestos)
            ---------------------------------------------------------
            , SUM(CASE WHEN FVR.tipo_imp = 5 
                       THEN (FVR.prec_vta * FVR.total_art) 
                       ELSE 0 END) AS reng_monto_sinimp
            
            , SUM(CASE WHEN FVR.tipo_imp = 5 
                       THEN (FVR.prec_vta * FVR.total_art) / NULLIF(FV.tasa, 0) 
                       ELSE 0 END) AS reng_monto_sinimp2
            ---------------------------------------------------------

            , SUM(FVR.reng_neto) AS reng_neto
            , SUM(FVR.reng_neto / NULLIF(FV.tasa, 0)) AS reng_neto2
            
            , SUM(FVR.pendiente) AS pendiente
            , SUM(FVR.pendiente2) AS pendiente2
            , FV.campo1 AS orden_compra_cliente
            , FVR.lote_asignado
            , (SELECT MAX(t.fecha) FROM saTasa AS t WHERE DATEDIFF(day, t.fecha, FV.fec_emis) >= 0 AND t.co_mone = FV.co_mone) AS Fecha_Coletilla
        FROM
            saFacturaVenta AS FV
            INNER JOIN saFacturaVentaReng AS FVR ON FVR.doc_num = FV.doc_num
            INNER JOIN saCliente AS CL ON CL.co_cli = FV.co_cli
            INNER JOIN saVendedor AS VE ON VE.co_ven = FV.co_ven
            INNER JOIN saTransporte AS TR ON TR.co_tran = FV.co_tran
            LEFT JOIN saCondicionPago AS CP ON CP.co_cond = FV.co_cond
            INNER JOIN saMoneda AS MO ON MO.co_mone = FV.co_mone
            INNER JOIN saArticulo AS ART ON ART.co_art = FVR.co_art
            LEFT JOIN saArtUnidad AS UNI ON UNI.co_art = ART.co_art AND UNI.co_uni = 'CAJ'
        WHERE
            FV.anulado = 0
            AND (@cCo_Numero_d IS NULL OR FV.doc_num >= @cCo_Numero_d)
            AND (@cCo_Numero_h IS NULL OR FV.doc_num <= @cCo_Numero_h)
            AND (@cCo_Sucursal IS NULL OR FV.co_sucu_in = @cCo_Sucursal)
        GROUP BY
            CL.cli_des, CL.ciudad, CL.nit, CL.campo1, CL.campo2, CL.campo3, CL.campo4, CL.campo5, CL.campo6, CL.campo7, CL.campo8
            , CL.rif, CL.nit, CL.telefonos, FV.campo2, CL.direc1, CL.dir_ent2, FV.campo4, VE.ven_des, TR.des_tran, CP.cond_des, MO.mone_des
            , FV.doc_num, FV.descrip, FV.co_cli, FV.co_tran, FV.co_mone, FV.co_ven, FV.co_cond, FV.fec_emis, FV.fec_venc, FV.fec_reg, FV.anulado, FV.status, FV.n_control, FV.ven_ter
            , FV.tasa, FV.porc_reca, FV.monto_reca, FV.otros3, FV.dir_ent, FV.comentario, FVR.doc_num, FVR.co_art, ART.art_des, UNI.equivalencia, ART.stock_pedido
            , FVR.co_alma, FVR.co_uni, FVR.sco_uni, FVR.co_precio, ART.item, ART.ref, FVR.prec_vta, FVR.prec_vta_om, FVR.tipo_imp, FVR.tipo_imp2, FVR.tipo_imp3
            , FVR.porc_imp, FVR.porc_imp2, FVR.porc_imp3, FV.campo1, FVR.lote_asignado, FV.porc_desc_glob, FV.otros1, FV.otros2, FVR.porc_desc;
    END