------------------------------------------------------------------
-- Versión: V2_CV Corregida (Auditoría Integral + Lotes Reais)
-- Fecha: 11/03/2026
------------------------------------------------------------------
CREATE PROCEDURE [dbo].[RepFormatoDevolucionClienteOM_Lote_V2_CV] 
    @sCo_Numero_d CHAR(20) = NULL ,
    @sCo_Numero_h CHAR(20) = NULL ,
    @sCo_Sucursal CHAR(6) = NULL ,
    @sCampOrderBy VARCHAR(16) = NULL ,
    @sDir VARCHAR(6) = NULL ,
    @bHeaderRep BIT = 0
AS 
    BEGIN
        SET NOCOUNT ON ;

        DECLARE @Tipo_doc CHAR(11) ;
        SET @Tipo_doc = 'devoventa' ;
		DECLARE @Direc VARCHAR(1000),@Telef VARCHAR(100), @Email VARCHAR(100) ;
		select @Direc = val_str from saAdiCampo where co_adicampo='DIR_FIS';
		select @Telef = val_str from saAdiCampo where co_adicampo='TELEF';
		select @Email = val_str from saAdiCampo where co_adicampo='EMAIL';
	
        SELECT
            @Direc AS DIRECCION_EMP, @Telef AS TELEFONO_EMP, @Email AS CORREO_EMP,
			CL.cli_des
			, cl.ciudad as NComercial
			, cl.zip AS SICA
			, CL.campo1
			, CL.campo2
			, CL.campo3
			, CL.campo4
			, CL.campo5
			, CL.campo6
			, CL.campo7
			, CL.campo8
			, CL.rif
			, CL.nit
			, CL.telefonos
			, FV.campo2 AS fax
			, CL.direc1
			, (CASE WHEN (FV.dir_ent IS NOT NULL AND len(ltrim(FV.dir_ent)) > 0) THEN FV.dir_ent ELSE CL.dir_ent2 END) AS dir_entrega
			, VE.ven_des
			, TR.des_tran
			, CP.cond_des
			, MO.mone_des
		/*Campos saNotaEntregaVenta*/ 
			, FV.nro_doc as doc_num
			, FV.descrip
			, FV.co_cli
			, FV.co_tran
			, FV.co_mone
			, FV.co_ven
            , FV.co_cond
			, FV.fec_emis
			, FV.fec_venc
			, FV.fec_reg
			, FV.anulado
			, FV.status
			, FV.n_control
			, FV.ven_ter
			, FV.tasa
            , isnull(FV.porc_desc_glob,0) AS porc_desc_glob
			
            -- FIX A: Proteccion contra division por cero en TASA
            , FV.monto_desc_glob, FV.monto_desc_glob / NULLIF(FV.tasa, 0) AS monto_desc_glob2
			, FV.porc_reca
            , FV.monto_reca, FV.monto_reca / NULLIF(FV.tasa, 0) AS monto_reca2
			, FV.total_bruto, FV.total_bruto / NULLIF(FV.tasa, 0) AS total_bruto2
            , FV.monto_imp, FV.monto_imp / NULLIF(FV.tasa, 0) AS monto_imp2
			, FV.monto_imp2 / NULLIF(FV.tasa, 0) AS monto_imp22, FV.monto_imp3
            , FV.otros1 / NULLIF(FV.tasa, 0) AS otros1
			, FV.otros2 / NULLIF(FV.tasa, 0) AS otros2
			, FV.otros3 / NULLIF(FV.tasa, 0) AS otros3
			, FV.total_neto, FV.total_neto / NULLIF(FV.tasa, 0) AS total_neto2
            , FV.saldo
			, FV.otros3 / NULLIF(FV.tasa, 0) AS otros3_2
			, FV.dir_ent
			, FV.comentario
            
		/*Campos saDevolucionClienteReng*/ 
			-- FIX C: Numero de renglon por factura
			, ROW_NUMBER() OVER (PARTITION BY FV.doc_num ORDER BY FVR.co_art ASC) AS reng_num 
            
			, FVR.co_art
			, ART.art_des
			, SUM(FVR.total_art) AS total_art
			
            -- FIX A: Proteccion contra division por cero en Equivalencia
            , CASE WHEN UNI.relacion = 0 THEN 
				SUM(FVR.total_art / NULLIF(UNI.equivalencia, 0))
			ELSE
				SUM(FVR.total_art * UNI.equivalencia)
			END AS cantidad
            
			, MAX(UNI.equivalencia) AS equivalencia
			, AVG(ART.stock_pedido) AS peso
            
			-- FIX B: Habilitacion de Lotes
			, LE.numero_lote
			, LE.fecha_inicio
			, LE.fecha_expiracion
            
			, FVR.co_alma
			, SUM(FVR.stotal_art) AS stotal_art
			, FVR.co_uni
			, FVR.sco_uni
			, FVR.co_precio
			, ART.modelo
			, art.item
			, art.ref
			, AVG(FVR.prec_vta) AS prec_vta
			, AVG(FVR.prec_vta / NULLIF(FV.tasa, 0)) AS prec_vta2
			, AVG(FVR.prec_vta_om) AS prec_vta_om
			, isnull(MAX(FVR.porc_desc), 0) porc_desc
			, SUM(FVR.monto_desc) AS monto_desc
			, SUM(FVR.monto_desc / NULLIF(FV.tasa, 0)) AS monto_desc2
			, FVR.tipo_imp
			, FVR.tipo_imp2
			, FVR.tipo_imp3
			, FVR.porc_imp
			, FVR.porc_imp2
			, FVR.porc_imp3
			, SUM(FVR.monto_imp) as reng_monto_imp
			, SUM(FVR.monto_imp / NULLIF(FV.tasa, 0)) AS reng_monto_imp2
			, SUM(FVR.monto_imp2 / NULLIF(FV.tasa, 0)) AS reng_monto_imp22
			, SUM(FVR.monto_imp3 / NULLIF(FV.tasa, 0)) AS reng_monto_imp3
            
            -- FIX D: Base Exenta en renglones
            , SUM(CASE WHEN FVR.tipo_imp = 5 THEN FVR.reng_neto ELSE 0 END) AS reng_monto_sinimp
            , SUM(CASE WHEN FVR.tipo_imp = 5 THEN FVR.reng_neto / NULLIF(FV.tasa, 0) ELSE 0 END) AS reng_monto_sinimp2
            
			, SUM(FVR.reng_neto) AS reng_neto
			, SUM(FVR.reng_neto / NULLIF(FV.tasa, 0)) AS reng_neto2
			, SUM(FVR.pendiente) AS pendiente
			, SUM(FVR.pendiente2) AS pendiente2
			, FV.campo1 AS comentario_fact
			, FVR.lote_asignado
			, FVR.num_doc AS nro_orig
			, F.tasa AS TasaF
			, F.total_bruto AS BrutoF
			, F.monto_imp AS IVAF
			, F.total_neto AS NetoF
        FROM
            saDevolucionCliente AS FV
            INNER JOIN saDevolucionClienteReng AS FVR ON FVR.doc_num = FV.doc_num
            INNER JOIN saCliente AS CL ON CL.co_cli = FV.co_cli
            INNER JOIN saVendedor AS VE ON VE.co_ven = FV.co_ven
            INNER JOIN saTransporte AS TR ON TR.co_tran = FV.co_tran
            LEFT JOIN saCondicionPago AS CP ON CP.co_cond = FV.co_cond
            INNER JOIN saMoneda AS MO ON MO.co_mone = FV.co_mone
            INNER JOIN saArticulo AS ART ON ART.co_art = FVR.co_art
			INNER JOIN saArtUnidad AS UNI ON UNI.co_art = ART.co_art AND FVR.co_uni = UNI.co_uni
            -- FIX B: Join a tabla de lotes desbloqueado
			LEFT JOIN saLoteEntrada AS LE ON LE.rowguid_reng = FVR.rowguid
			LEFT JOIN saFacturaVenta F ON F.doc_num = FVR.num_doc
        WHERE
            ( ( @sCo_Numero_d IS NULL
                OR FV.doc_num >= @sCo_Numero_d
              )
              AND ( @sCo_Numero_h IS NULL
                    OR FV.doc_num <= @sCo_Numero_h
                  )
            )
            AND ( FV.anulado = 0 )
            AND ( @sCo_Sucursal IS NULL
                  OR @sCo_Sucursal = FV.co_sucu_in
                )
		GROUP BY 
			CL.cli_des, cl.ciudad, cl.zip, CL.campo1, CL.campo2, CL.campo3, CL.campo4, CL.campo5, CL.campo6, CL.campo7, CL.campo8
			, CL.rif, CL.nit, CL.telefonos, FV.campo2, CL.direc1, FV.dir_ent, CL.dir_ent2, VE.ven_des, TR.des_tran, CP.cond_des, MO.mone_des
			, FV.nro_doc, FV.doc_num, FV.descrip, FV.co_cli, FV.co_tran, FV.co_mone, FV.co_ven, FV.co_cond, FV.fec_emis, FV.fec_venc, FV.fec_reg
			, FV.anulado, FV.status, FV.n_control, FV.ven_ter, FV.tasa, FV.porc_desc_glob, FV.monto_desc_glob, FV.porc_reca, FV.monto_reca
            , FV.otros1, FV.otros2, FV.otros3, FV.total_neto, FV.saldo, FV.comentario, FV.total_bruto, FV.monto_imp, FV.monto_imp2, FV.monto_imp3
			, FVR.co_art, ART.art_des, FVR.co_alma, FVR.co_uni, FVR.sco_uni, FVR.co_precio, ART.modelo, art.item, art.ref
			, FVR.tipo_imp, FVR.tipo_imp2, FVR.tipo_imp3, FVR.porc_imp, FVR.porc_imp2, FVR.porc_imp3
			, FV.campo1, FVR.num_doc, F.tasa, F.total_bruto, F.monto_imp, F.total_neto, UNI.relacion
            -- FIX B: Agrupacion incluye campos de Lote
            , LE.numero_lote, LE.fecha_inicio, LE.fecha_expiracion, FVR.lote_asignado
    END
