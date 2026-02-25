/*=============================================

 Author:		SOFTECH SISTEMAS

 Create date: <10/09/2010>

 Modify date: <12/01/2018>

 Last Update: 2021-02-20

 Description:	<Movimientos de Inventarios por Articulo X Lote Asignados>

=============================================*/

CREATE   PROCEDURE [dbo].[RepMovimientoInventarioxArticuloXlote]

    @sCo_Art_d CHAR(30) = NULL ,

    @sCo_Art_h CHAR(30) = NULL ,

    @dCo_fecha_d DATETIME = NULL ,

    @dCo_fecha_h DATETIME = NULL ,

    @sCo_Almacen CHAR(6) = NULL ,

    @sCo_Linea_d CHAR(6) = NULL ,

    @sCo_Linea_h CHAR(6) = NULL ,

    @sCo_Categoria_d CHAR(6) = NULL ,

    @sCo_Categoria_h CHAR(6) = NULL ,

    @sCo_Movimiento CHAR(4) = NULL ,

    @sCostos CHAR(4) = NULL ,

    @sNumero_Lote CHAR(20) = NULL ,

    @sAsignacion CHAR(20) = NULL ,

    @sCo_Sucursal CHAR(6) = NULL ,

    @sCampOrderBy VARCHAR(16) = NULL ,

    @sDir VARCHAR(6) = NULL ,

    @bHeaderRep BIT = 0

AS

    BEGIN

        SET NOCOUNT ON ;





        IF ( @sCo_Movimiento IS NULL

             OR @sCo_Movimiento = 'TODO'

           )

            SET @sCo_Movimiento = NULL



        IF @sAsignacion IS NULL

            SET @sAsignacion = '4'



        IF @dCo_fecha_h IS NOT NULL

            SET @dCo_fecha_h = DATEADD(ss, -1, DATEADD(day, 1, @dCo_fecha_h))



        IF @sCostos IS NULL

            OR @sCostos = 'NO'

            SET @sCostos = NULL



        SET @dCo_fecha_d = dbo.fechasimple(@dCo_fecha_d)

        SET @dCo_fecha_h = dbo.fechasimple(@dCo_fecha_h)





        SELECT

            A.*, B.StockInic, B.StockFinal, CASE WHEN @sCostos = 'SI' THEN '1'

                                                 ELSE '0'

                                            END AS detalle

        FROM

            (

	--1saFacturaCompraReng

              SELECT

                A.co_art, A.art_des, ISNULL(dbo.ArtUnidadBase(FCR.co_art, FCR.co_uni, FCR.total_art), 0) AS total_art,

                FCR.co_uni, ISNULL(FCR.total, 0) AS total, FCR.total * CASE WHEN FC.anulado = 1 THEN 0

                                                                            ELSE 1

                                                                       END AS total_entrada, 0.00 AS total_salida,

                AU2.co_uni AS co_uni_base, FCR.co_alma, dbo.fechasimple(FC.fec_emis) AS fecha, FCR.reng_num, FCR.doc_num,

                FC.anulado AS anulado, FC.co_prov, '' AS co_cli, 'COMP' AS tipo,

				A.tipo AS tipo_art,

                ISNULL(FCR.numero_lote, 'Por Asignar') AS numero_lote

              FROM

                saArticulo AS A

                LEFT JOIN ( SELECT

                                DVR.co_art, DVR.doc_num, DVR.co_uni, DVR.co_alma, DVR.reng_num, DEVR.total,

                                DVR.total_art, DVR.rowguid, DVR.tipo_doc, DEVR.numero_lote

                            FROM

                                saFacturaCompraReng AS DVR

                                INNER JOIN (

											SELECT

                                                SUM(SL.cantidad) AS total, DEVR.doc_num, DEVR.co_alma, DEVR.co_art,

                                                DEVR.reng_num, SL.numero_lote



                                             FROM

                                                saFacturaCompraReng AS DEVR

                                                LEFT JOIN saLoteEntrada AS SL ON DEVR.rowguid = SL.rowguid_reng

                                                                                 AND DEVR.co_art = SL.co_art

                                                                                 AND SL.tipo_doc = 'COMP'

                                             WHERE

                                                ( DEVR.tipo_doc <> 'NREC'

                                                  OR DEVR.tipo_doc IS NULL

                                                )

                                                AND ( @sCo_Art_d IS NULL

                                                      OR DEVR.co_art >= @sCo_Art_d

                                                    )

                                                AND ( @sCo_Art_h IS NULL

                                                      OR DEVR.co_art <= @sCo_Art_h

                                                    )

                                             GROUP BY

                                                DEVR.doc_num, DEVR.co_art, DEVR.co_alma, DEVR.reng_num, SL.numero_lote

                                           ) AS DEVR ON DVR.doc_num = DEVR.doc_num

                                                        AND DVR.co_alma = DEVR.co_alma

                                                        AND DVR.co_art = DEVR.co_art

                                                        AND DVR.reng_num = DEVR.reng_num

                            WHERE

                                ( DVR.tipo_doc <> 'NREC'

                                  OR DVR.tipo_doc IS NULL

                                )

                                AND ( @sCo_Art_d IS NULL

                                      OR DVR.co_art >= @sCo_Art_d

                                    )

                                AND ( @sCo_Art_h IS NULL

                                      OR DVR.co_art <= @sCo_Art_h

                                    )

                          ) AS FCR ON A.co_art = FCR.co_art

                                      AND A.maneja_lote = 1

                                      AND ( FCR.tipo_doc <> 'NREC'

                                            OR FCR.tipo_doc IS NULL

                                          )

                INNER JOIN saFacturaCompra FC ON FCR.doc_num = FC.doc_num

                INNER JOIN saArtUnidad AS AU ON AU.co_art = FCR.co_art

                                                AND AU.co_uni = FCR.co_uni

                LEFT JOIN saArtUnidad AS AU2 ON AU2.co_art = A.co_art

                                                AND AU2.uni_principal = 1

              WHERE

                ( @sCo_Art_d IS NULL

                  OR A.co_art >= @sCo_Art_d

                )

                AND ( @sCo_Art_h IS NULL

                      OR A.co_art <= @sCo_Art_h

                    )

                AND ( ( @dCo_fecha_d IS NULL

                        OR dbo.fechasimple(FC.fec_emis) >= @dCo_fecha_d

                      )

                      AND ( @dCo_fecha_h IS NULL

                            OR dbo.fechasimple(FC.fec_emis) <= @dCo_fecha_h

                          )

                    )

                AND ( @sCo_Almacen IS NULL

                      OR FCR.co_alma = @sCo_Almacen

                    )

                AND ( @sCo_Linea_d IS NULL

                      OR A.co_lin >= @sCo_Linea_d

                    )

                AND ( @sCo_Linea_h IS NULL

                      OR A.co_lin <= @sCo_Linea_h

                    )

                AND ( @sCo_Categoria_d IS NULL

                      OR A.co_cat >= @sCo_Categoria_d

                    )

                AND ( @sCo_Categoria_h IS NULL

                      OR A.co_cat <= @sCo_Categoria_h

                    )

                AND ( @sNumero_Lote IS NULL

                      OR FCR.numero_lote = @sNumero_Lote

                    )

                AND ( @sCo_Sucursal IS NULL

                      OR A.co_sucu_in = @sCo_Sucursal

                    )

              UNION ALL

	--2saFacturaVentaReng

              SELECT 	DISTINCT

                A.co_art, A.art_des, ISNULL(dbo.ArtUnidadBase(A.co_art, FVR.co_uni, FVR.total_art), 0) AS total_art,

                FVR.co_uni, ISNULL(FVR.total, 0) AS total, 0.00 AS total_entrada,

                FVR.total * CASE WHEN FR.anulado = 1 THEN 0

                                 ELSE 1

                            END * -1 AS total_salida, AU2.co_uni AS co_uni_base, FVR.co_alma,

                dbo.fechasimple(FR.fec_emis) AS fecha, FVR.reng_num, FVR.doc_num, FR.anulado AS anulado, '' AS co_prov,

                FR.co_cli, 'FACT' AS tipo,

				A.tipo AS tipo_art,

                ISNULL(FVR.numero_lote, 'Por Asignar') AS numero_lote

              FROM

                saArticulo AS A

                LEFT JOIN ( SELECT

                                DVR.co_art, DVR.doc_num, DVR.co_uni, DVR.co_alma, DVR.reng_num, DEVR.total,

                                DVR.total_art, DVR.rowguid, DVR.tipo_doc, DEVR.numero_lote

                            FROM

                                saFacturaVentaReng AS DVR

                                INNER JOIN (

											SELECT

												  SUM(SL.cantidad) AS total, DEVR.doc_num, DEVR.co_alma, DEVR.co_art,

												  DEVR.reng_num, SL.numero_lote

											 FROM

												  saFacturaVentaReng AS DEVR

												  LEFT JOIN saLoteSalida AS SL ON DEVR.rowguid = SL.rowguid_reng

																			   AND DEVR.co_art = SL.co_art

																			   AND SL.tipo_doc = 'FACT'

-- 												  LEFT JOIN saLoteEntrada AS SE ON SL.rowguid_lote = SE.rowguid

                                             WHERE

                                                ( DEVR.tipo_doc <> 'NENT'

                                                  OR DEVR.tipo_doc IS NULL

                                                  AND ( @sCo_Art_d IS NULL

                                                        OR DEVR.co_art >= @sCo_Art_d

                                                      )

                                                  AND ( @sCo_Art_h IS NULL

                                                        OR DEVR.co_art <= @sCo_Art_h

                                                      )

                                                )

                                             GROUP BY

                                                DEVR.co_art, DEVR.co_alma, DEVR.doc_num, DEVR.reng_num, SL.numero_lote

                                           ) AS DEVR ON DVR.doc_num = DEVR.doc_num

                                                        AND DVR.co_alma = DEVR.co_alma

                                                        AND DVR.co_art = DEVR.co_art

                                                        AND DVR.reng_num = DEVR.reng_num

                            WHERE

                                ( DVR.tipo_doc <> 'NENT'

                                  OR DVR.tipo_doc IS NULL

                                )

                                AND ( ( @sCo_Art_d IS NULL

                                        OR DEVR.co_art >= @sCo_Art_d

                                      )

                                      AND ( @sCo_Art_h IS NULL

                                            OR DEVR.co_art <= @sCo_Art_h

                                          )

                                    )

                          ) AS FVR ON A.co_art = FVR.co_art

                                      AND A.maneja_lote = 1

                                      AND ( FVR.tipo_doc <> 'NENT'

                                            OR FVR.tipo_doc IS NULL

                                          )

                INNER JOIN saFacturaVenta FR ON FVR.doc_num = FR.doc_num

                INNER JOIN saArtUnidad AS AU ON AU.co_art = A.co_art

                                                AND AU.co_uni = FVR.co_uni

                LEFT JOIN saArtUnidad AS AU2 ON AU2.co_art = A.co_art

                                                AND AU2.uni_principal = 1

              WHERE

                ( @sCo_Art_d IS NULL

                  OR A.co_art >= @sCo_Art_d

                )

                AND ( @sCo_Art_h IS NULL

                      OR A.co_art <= @sCo_Art_h

                    )

                AND ( ( @dCo_fecha_d IS NULL

                        OR dbo.fechasimple(FR.fec_emis) >= @dCo_fecha_d

                      )

                      AND ( @dCo_fecha_h IS NULL

                            OR dbo.fechasimple(FR.fec_emis) <= @dCo_fecha_h

                          )

                    )

                AND ( @sCo_Almacen IS NULL

                      OR FVR.co_alma = @sCo_Almacen

                    )

                AND ( @sCo_Linea_d IS NULL

                      OR A.co_lin >= @sCo_Linea_d

                    )

                AND ( @sCo_Linea_h IS NULL

                      OR A.co_lin <= @sCo_Linea_h

                    )

                AND ( @sCo_Categoria_d IS NULL

                      OR A.co_cat >= @sCo_Categoria_d

                    )

                AND ( @sCo_Categoria_h IS NULL

                      OR A.co_cat <= @sCo_Categoria_h

                    )

                AND ( @sNumero_Lote IS NULL

                      OR FVR.numero_lote = @sNumero_Lote

                    )

                AND ( @sCo_Sucursal IS NULL

                      OR A.co_sucu_in = @sCo_Sucursal

                    )

              UNION ALL

	--3saNotaRecepcionCompraReng

              SELECT

                A.co_art, A.art_des, ISNULL(dbo.ArtUnidadBase(A.co_art, NRCR.co_uni, NRCR.total_art), 0) AS total_art,

                NRCR.co_uni, ISNULL(NRCR.total, 0) AS total, NRCR.total * CASE WHEN NR.anulado = 1 THEN 0

                                                                               ELSE 1

                                                                          END AS total_entrada, 0.00 AS total_salida,

                AU2.co_uni AS co_uni_base, NRCR.co_alma, dbo.fechasimple(NR.fec_emis) AS fecha, NRCR.reng_num,

                NRCR.doc_num, NR.anulado AS anulado, NR.co_prov, '' AS co_cli, 'NREC' AS tipo,

                A.tipo AS tipo_art, ISNULL(NRCR.numero_lote, 'Por Asignar') AS numero_lote

              FROM

                saArticulo AS A

                LEFT JOIN ( SELECT

                                DVR.co_art, DVR.doc_num, DVR.co_uni, DVR.co_alma, DVR.reng_num, DEVR.total,

                                DVR.total_art, DVR.rowguid, DEVR.numero_lote

                            FROM

                                saNotaRecepcionCompraReng AS DVR

                                INNER JOIN ( SELECT

                                                SUM(DEVR.total_art) AS total, DEVR.doc_num, DEVR.co_alma, DEVR.co_art,

                                                SL.numero_lote, DEVR.reng_num

                                             FROM

                                                saNotaRecepcionCompraReng AS DEVR

                                                LEFT JOIN saLoteEntrada AS SL ON DEVR.rowguid = SL.rowguid_reng

                                                                                 AND DEVR.co_art = SL.co_art

                                                                                 AND SL.tipo_doc = 'NREC'

                                             GROUP BY

                                                DEVR.doc_num, DEVR.co_alma, DEVR.reng_num, DEVR.co_art, SL.numero_lote

                                           ) AS DEVR ON DVR.doc_num = DEVR.doc_num

                                                        AND DVR.co_alma = DEVR.co_alma

                                                        AND DVR.co_art = DEVR.co_art

                                                        AND DVR.reng_num = DEVR.reng_num

                          ) AS NRCR ON A.co_art = NRCR.co_art

                                       AND A.maneja_lote = 1

                INNER JOIN saNotaRecepcionCompra NR ON NRCR.doc_num = NR.doc_num

                INNER JOIN saArtUnidad AS AU ON AU.co_art = NRCR.co_art

                                                AND AU.co_uni = NRCR.co_uni

                LEFT JOIN saArtUnidad AS AU2 ON AU2.co_art = A.co_art

                                                AND AU2.uni_principal = 1

              WHERE

                ( @sCo_Art_d IS NULL

                  OR A.co_art >= @sCo_Art_d

                )

                AND ( @sCo_Art_h IS NULL

                      OR A.co_art <= @sCo_Art_h

                    )

                AND ( ( @dCo_fecha_d IS NULL

                        OR dbo.fechasimple(NR.fec_emis) >= @dCo_fecha_d

                      )

                      AND ( @dCo_fecha_h IS NULL

                            OR dbo.fechasimple(NR.fec_emis) <= @dCo_fecha_h

                          )

                    )

                AND ( @sCo_Almacen IS NULL

                      OR NRCR.co_alma = @sCo_Almacen

                    )

                AND ( @sCo_Linea_d IS NULL

                      OR A.co_lin >= @sCo_Linea_d

                    )

                AND ( @sCo_Linea_h IS NULL

                      OR A.co_lin <= @sCo_Linea_h

                    )

                AND ( @sCo_Categoria_d IS NULL

                      OR A.co_cat >= @sCo_Categoria_d

                    )

                AND ( @sCo_Categoria_h IS NULL

                      OR A.co_cat <= @sCo_Categoria_h

                    )

                AND ( @sNumero_Lote IS NULL

                      OR NRCR.numero_lote = @sNumero_Lote

                    )

                AND ( @sCo_Sucursal IS NULL

                      OR A.co_sucu_in = @sCo_Sucursal

                    )

              UNION ALL

	--4saNotaEntregaVentaReng

              SELECT

                A.co_art, A.art_des, ISNULL(dbo.ArtUnidadBase(A.co_art, NEVR.co_uni, NEVR.total_art), 0) AS total_art,

                AU.co_uni, ISNULL(NEVR.total, 0) AS total, 0.00 AS total_entrada,

                NEVR.total * CASE WHEN ER.anulado = 1 THEN 0

                                  ELSE 1

                             END * -1 AS total_salida, AU2.co_uni AS co_uni_base, NEVR.co_alma,

                dbo.fechasimple(ER.fec_emis) AS fecha, NEVR.reng_num, NEVR.doc_num, ER.anulado AS anulado, '' co_prov,

                ER.co_cli, 'NENT' AS tipo,

				A.tipo AS tipo_art,

                ISNULL(NEVR.numero_lote, 'Por Asignar') AS numero_lote

              FROM

                saArticulo AS A

                LEFT JOIN ( SELECT

                                DVR.co_art, DVR.doc_num, DVR.co_uni, DVR.co_alma, DVR.reng_num, DEVR.total,

                                DVR.total_art, DVR.rowguid, DEVR.numero_lote

                            FROM

                                saNotaEntregaVentaReng AS DVR

                                INNER JOIN (

											SELECT

                                                SUM(DEVR.total_art) AS total, DEVR.doc_num, DEVR.co_alma, DEVR.co_art,

                                                SL.numero_lote, DEVR.reng_num

                                             FROM

                                                saNotaEntregaVentaReng AS DEVR

                                                LEFT JOIN saLoteSalida AS SL ON DEVR.rowguid = SL.rowguid_reng

                                                                                AND DEVR.co_art = SL.co_art

                                                                                AND SL.tipo_doc = 'NENT'

-- 												LEFT JOIN saLoteEntrada AS SE ON SL.rowguid_lote = SE.rowguid

                                             GROUP BY

                                                DEVR.doc_num, DEVR.co_alma, DEVR.co_art, DEVR.reng_num, SL.numero_lote



                                           ) AS DEVR ON DVR.doc_num = DEVR.doc_num

                                                        AND DVR.co_alma = DEVR.co_alma

                                                        AND DVR.co_art = DEVR.co_art

                                                        AND DVR.reng_num = DEVR.reng_num

                          ) AS NEVR ON A.co_art = NEVR.co_art

                                       AND A.maneja_lote = 1

                INNER JOIN saNotaEntregaVenta ER ON NEVR.doc_num = ER.doc_num



                INNER JOIN saArtUnidad AS AU ON AU.co_art = NEVR.co_art

                                                AND au.co_uni = NEVR.co_uni

                LEFT JOIN saArtUnidad AS AU2 ON AU2.co_art = A.co_art

                                                AND AU2.uni_principal = 1

              WHERE

                ( @sCo_Art_d IS NULL

                  OR A.co_art >= @sCo_Art_d

                )

                AND ( @sCo_Art_h IS NULL

                      OR A.co_art <= @sCo_Art_h

                    )

                AND ( ( @dCo_fecha_d IS NULL

                        OR dbo.fechasimple(ER.fec_emis) >= @dCo_fecha_d

                      )

                      AND ( @dCo_fecha_h IS NULL

                            OR dbo.fechasimple(ER.fec_emis) <= @dCo_fecha_h

                          )

                    )

                AND ( @sCo_Almacen IS NULL

                      OR NEVR.co_alma = @sCo_Almacen

                    )

                AND ( @sCo_Linea_d IS NULL

                      OR A.co_lin >= @sCo_Linea_d

                    )

                AND ( @sCo_Linea_h IS NULL

                      OR A.co_lin <= @sCo_Linea_h

                    )

                AND ( @sCo_Categoria_d IS NULL

                      OR A.co_cat >= @sCo_Categoria_d

                    )

                AND ( @sCo_Categoria_h IS NULL

                      OR A.co_cat <= @sCo_Categoria_h

                    )

                AND ( @sNumero_Lote IS NULL

                      OR NEVR.numero_lote = @sNumero_Lote

                    )

                AND ( @sCo_Sucursal IS NULL

                      OR A.co_sucu_in = @sCo_Sucursal

                    )

              UNION ALL

	--5.saDevolucionClienteReng

              SELECT

                A.co_art, A.art_des, ISNULL(dbo.ArtUnidadBase(A.co_art, DVR.co_uni, DVR.total_art), 0) AS total_art,

                AU.co_uni AS co_uni, ISNULL(DVR.total, 0) AS total, DVR.total * CASE WHEN DR.anulado = 1 THEN 0

                                                                                     ELSE 1

                                                                                END AS total_entrada,

                0.00 AS total_salida, AU2.co_uni AS co_uni_base, DVR.co_alma, dbo.fechasimple(DR.fec_emis) AS fecha,

                DVR.reng_num, DVR.doc_num, DR.anulado AS anulado, '' co_prov, DR.co_cli, 'DCLI' AS tipo,

                A.tipo AS tipo_art, ISNULL(DVR.numero_lote, 'Por Asignar') AS numero_lote

              FROM

                saArticulo AS A

                LEFT JOIN ( SELECT

                                DVR.co_art, DVR.doc_num, DVR.co_uni, DVR.co_alma, DVR.reng_num, DEVR.total,

                                DVR.total_art, DVR.rowguid, DEVR.numero_lote

                            FROM

                                saDevolucionClienteReng AS DVR

                                INNER JOIN (

											SELECT

                                                SUM(SL.cantidad) AS total, DEVR.doc_num, DEVR.co_alma, DEVR.co_art,

                                                SL.numero_lote, DEVR.reng_num

                                             FROM

                                                saDevolucionClienteReng AS DEVR

                                                LEFT JOIN saLoteEntrada AS SL ON DEVR.rowguid = SL.rowguid_reng

                                                                                 AND DEVR.co_art = SL.co_art

                                                                                 AND SL.tipo_doc = 'DCLI'

                                             GROUP BY

                                                DEVR.doc_num, DEVR.co_alma, DEVR.co_art, DEVR.reng_num, SL.numero_lote

                                           ) AS DEVR ON DVR.doc_num = DEVR.doc_num

                                                        AND DVR.co_alma = DEVR.co_alma

                                                        AND DVR.co_art = DEVR.co_art

                                                        AND DVR.reng_num = DEVR.reng_num

                          ) AS DVR ON A.co_art = DVR.co_art

                                      AND A.maneja_lote = 1

                INNER JOIN saDevolucionCliente DR ON DVR.doc_num = DR.doc_num

                INNER JOIN saArtUnidad AS AU ON AU.co_art = DVR.co_art

                                                AND DVR.co_uni = AU.co_uni

                LEFT JOIN saArtUnidad AS AU2 ON AU2.co_art = A.co_art

                                                AND AU2.uni_principal = 1

              WHERE

                ( @sCo_Art_d IS NULL

                  OR A.co_art >= @sCo_Art_d

                )

                AND ( @sCo_Art_h IS NULL

                      OR A.co_art <= @sCo_Art_h

                    )

                AND ( ( @dCo_fecha_d IS NULL

                        OR dbo.fechasimple(DR.fec_emis) >= @dCo_fecha_d

                      )

                      AND ( @dCo_fecha_h IS NULL

                            OR dbo.fechasimple(DR.fec_emis) <= @dCo_fecha_h

                          )

                    )

                AND ( @sCo_Almacen IS NULL

                      OR DVR.co_alma = @sCo_Almacen

                    )

                AND ( @sCo_Linea_d IS NULL

                      OR A.co_lin >= @sCo_Linea_d

                    )

                AND ( @sCo_Linea_h IS NULL

                      OR A.co_lin <= @sCo_Linea_h

                    )

                AND ( @sCo_Categoria_d IS NULL

                      OR A.co_cat >= @sCo_Categoria_d

                    )

                AND ( @sCo_Categoria_h IS NULL

                      OR A.co_cat <= @sCo_Categoria_h

                    )

                AND ( @sNumero_Lote IS NULL

                      OR DVR.numero_lote = @sNumero_Lote

                    )

                AND ( @sCo_Sucursal IS NULL

                      OR A.co_sucu_in = @sCo_Sucursal

                    )

              UNION ALL

	--7saDevolucionProveedorReng

              SELECT

			DISTINCT

                A.co_art, A.art_des, ISNULL(dbo.ArtUnidadBase(A.co_art, DEVR.co_uni, DEVR.total_art), 0) AS total_art,

                AU.co_uni, ISNULL(DEVR.total, 0) AS total, 0.00 AS total_entrada,

                DEVR.total * CASE WHEN DP.anulado = 1 THEN 0

                                  ELSE 1

                             END * -1 AS total_salida, AU2.co_uni AS co_uni_base, DEVR.co_alma,

                dbo.fechasimple(DP.fec_emis) AS fecha, DEVR.reng_num, DEVR.doc_num, DP.anulado AS anulado, DP.co_prov,

                '' AS co_cli, 'DPRO' AS tipo,

				A.tipo AS tipo_art,

                ISNULL(DEVR.numero_lote, 'Por Asignar') AS numero_lote

              FROM

                saArticulo AS A

                LEFT JOIN ( SELECT

                                DVR.co_art, DVR.doc_num, DVR.co_uni, DVR.co_alma, DVR.reng_num, DEVR.total,

                                DVR.total_art, DVR.rowguid, DEVR.numero_lote

                            FROM

                                saDevolucionProveedorReng AS DVR

                                INNER JOIN ( SELECT



                                                SUM( SL.cantidad) AS total, DEVR.doc_num, DEVR.co_alma, DEVR.co_art,

                                                SL.numero_lote, DEVR.reng_num

                                             FROM

                                                saDevolucionProveedorReng AS DEVR

                                                LEFT JOIN saLoteSalida AS SL ON DEVR.rowguid = SL.rowguid_reng

                                                                                AND DEVR.co_art = SL.co_art

                                                                                AND SL.tipo_doc = 'DPRO'

-- 												LEFT JOIN saLoteEntrada AS SE ON SL.rowguid_lote = SE.rowguid

                                             WHERE

                                                ( @sCo_Art_d IS NULL

                                                  OR DEVR.co_art >= @sCo_Art_d

                                                )

                                                AND ( @sCo_Art_h IS NULL

                                                      OR DEVR.co_art <= @sCo_Art_h

                                                    )

                                                AND ( @sCo_Almacen IS NULL

                                                      OR DEVR.co_alma = @sCo_Almacen

                                                    )

                                             GROUP BY

                                                DEVR.doc_num, DEVR.co_alma, DEVR.co_art, DEVR.reng_num, SL.numero_lote

                                           ) AS DEVR ON DVR.doc_num = DEVR.doc_num

                                                        AND DVR.co_alma = DEVR.co_alma

                                                        AND DVR.co_art = DEVR.co_art

                                                        AND DVR.reng_num = DEVR.reng_num

                            WHERE

                                ( @sCo_Art_d IS NULL

                                  OR DVR.co_art >= @sCo_Art_d

                                )

                                AND ( @sCo_Art_h IS NULL

                                      OR DVR.co_art <= @sCo_Art_h

                                    )

                                AND ( @sCo_Almacen IS NULL

                                      OR DVR.co_alma = @sCo_Almacen

                                    )

                          ) AS DEVR ON A.co_art = DEVR.co_art

                                       AND A.maneja_lote = 1

                INNER JOIN saDevolucionProveedor DP ON DEVR.doc_num = DP.doc_num

                INNER JOIN saArtUnidad AS AU ON AU.co_art = DEVR.co_art

                                                AND DEVR.co_uni = AU.co_uni

                LEFT JOIN saArtUnidad AS AU2 ON AU2.co_art = A.co_art

                                                AND AU2.uni_principal = 1

              WHERE

                ( @sCo_Art_d IS NULL

                  OR A.co_art >= @sCo_Art_d

                )

                AND ( @sCo_Art_h IS NULL

                      OR A.co_art <= @sCo_Art_h

                    )

                AND ( ( @dCo_fecha_d IS NULL

                        OR dbo.fechasimple(DP.fec_emis) >= @dCo_fecha_d

                      )

                      AND ( @dCo_fecha_h IS NULL

                            OR dbo.fechasimple(DP.fec_emis) <= @dCo_fecha_h

                          )

                    )

                AND ( @sCo_Almacen IS NULL

                      OR DEVR.co_alma = @sCo_Almacen

                    )

                AND ( @sCo_Linea_d IS NULL

                      OR A.co_lin >= @sCo_Linea_d

                    )

                AND ( @sCo_Linea_h IS NULL

                      OR A.co_lin <= @sCo_Linea_h

                    )

                AND ( @sCo_Categoria_d IS NULL

                      OR A.co_cat >= @sCo_Categoria_d

                    )

                AND ( @sCo_Categoria_h IS NULL

                      OR A.co_cat <= @sCo_Categoria_h

                    )

                AND ( @sNumero_Lote IS NULL

                      OR DEVR.numero_lote = @sNumero_Lote

                    )

                AND ( @sCo_Sucursal IS NULL

                      OR A.co_sucu_in = @sCo_Sucursal

                    )

              UNION ALL

	--8saAjusteReng



              SELECT

                A.co_art, A.art_des, ISNULL(dbo.ArtUnidadBase(AR.co_art, AR.co_uni, AR.total_art), 0) AS total_art,

                AU.co_uni, ISNULL(AR.total, 0) AS total,

                CASE WHEN ST.tipo_trans = '0' THEN AR.total_entrada * CASE WHEN AJ.anulado = 1 THEN 0

                                                                           ELSE 1

                                                                      END

                     ELSE 0

                END AS total_entrada,

                ( CASE WHEN ST.tipo_trans = '1' THEN AR.total_SALIDA * CASE WHEN AJ.anulado = 1 THEN 0

                                                                            ELSE 1

                                                                       END

                       ELSE 0

                  END ) * -1 AS total_salida, AU2.co_uni AS co_uni_base, AR.co_alma, dbo.fechasimple(AJ.fecha) AS fecha,

                AR.reng_num, AJ.ajue_num, AJ.anulado AS anulado, '' co_prov, '' co_cli, 'AJUS' AS tipo,

				A.tipo AS tipo_art,

                ISNULL(AR.numero_lote, 'Por Asignar') AS numero_lote

              FROM

                saArticulo AS A

                LEFT JOIN ( SELECT

                                0.00 AS total_entrada, ISNULL(SUM(SL.cantidad),0.00000) AS total_salida, ISNULL(SUM(DEVR.total_art),0.00000) AS total,

                                DEVR.ajue_num, ISNULL(SUM(DEVR.total_art),0.00000) AS total_art, DEVR.co_alma, DEVR.rowguid, DEVR.co_art,

                                DEVR.reng_num, DEVR.co_uni, SL.numero_lote, TJ.co_tipo

                            FROM

                                saAjusteReng AS DEVR

                                LEFT JOIN saLoteSalida AS SL ON DEVR.rowguid = SL.rowguid_reng

                                                                AND SL.co_art = DEVR.co_art

                                                                AND SL.tipo_doc = 'AJUS'

-- 								LEFT JOIN saLoteEntrada AS SE ON SL.rowguid_lote = SE.rowguid

                                LEFT JOIN saTipoAjuste AS TJ ON DEVR.co_tipo = TJ.co_tipo



                            WHERE

                                TJ.tipo_trans = '1'

                            GROUP BY

                                DEVR.ajue_num, DEVR.co_alma, DEVR.rowguid, DEVR.co_art, DEVR.reng_num, DEVR.co_uni,

                                SL.numero_lote, TJ.co_tipo

                            UNION ALL

                            SELECT

                                ISNULL(SUM(cantidad),0.00000) AS total_entrada, 0.00 AS total_salida, ISNULL(SUM(cantidad),0.00000) AS total,

                                DEVR.ajue_num, ISNULL(SUM(DEVR.total_art),0.00000) AS total_art, DEVR.co_alma, DEVR.rowguid, DEVR.co_art,

                                DEVR.reng_num, DEVR.co_uni, SL.numero_lote, TJ.co_tipo

                            FROM

                                saAjusteReng AS DEVR

                                LEFT JOIN saLoteEntrada AS SL ON DEVR.rowguid = SL.rowguid_reng

                                                                 AND SL.co_art = DEVR.co_art

                                                                 AND SL.tipo_doc = 'AJUS'

                                INNER JOIN saTipoAjuste AS TJ ON DEVR.co_tipo = TJ.co_tipo

                            WHERE

                                TJ.tipo_trans = '0'

                            GROUP BY

                                DEVR.ajue_num, DEVR.co_alma, DEVR.rowguid, DEVR.co_art, DEVR.reng_num, DEVR.co_uni,

                                SL.numero_lote, TJ.co_tipo

                          ) AS AR ON A.co_art = AR.co_art

                                     AND A.maneja_lote = 1

                INNER JOIN saAjuste AJ ON AR.ajue_num = AJ.ajue_num

                INNER JOIN saArtUnidad AS AU ON AU.co_art = AR.co_art

                                                AND AU.co_uni = AR.co_uni

                INNER JOIN saTipoAjuste ST ON Ar.co_tipo = ST.co_tipo

                LEFT JOIN saArtUnidad AS AU2 ON AU2.co_art = A.co_art

                                                AND AU2.uni_principal = 1

              WHERE

                ( @sCo_Art_d IS NULL

                  OR A.co_art >= @sCo_Art_d

                )

                AND ( @sCo_Art_h IS NULL

                      OR A.co_art <= @sCo_Art_h

                    )

                AND ( ( @dCo_fecha_d IS NULL

                        OR dbo.fechasimple(AJ.fecha) >= @dCo_fecha_d

                      )

                      AND ( @dCo_fecha_h IS NULL

                            OR dbo.fechasimple(AJ.fecha) <= @dCo_fecha_h

                          )

                    )

                AND ( @sCo_Almacen IS NULL

                      OR AR.co_alma = @sCo_Almacen

                    )

                AND ( @sCo_Linea_d IS NULL

                      OR A.co_lin >= @sCo_Linea_d

                    )

                AND ( @sCo_Linea_h IS NULL

                      OR A.co_lin <= @sCo_Linea_h

                    )

                AND ( @sCo_Categoria_d IS NULL

                      OR A.co_cat >= @sCo_Categoria_d

                    )

                AND ( @sCo_Categoria_h IS NULL

                      OR A.co_cat <= @sCo_Categoria_h

                    )

                AND ( @sNumero_Lote IS NULL

                      OR AR.numero_lote = @sNumero_Lote

                    )

                AND ( @sCo_Sucursal IS NULL

                      OR A.co_sucu_in = @sCo_Sucursal

                    )

              UNION ALL

              --Nota de Despacho

			    SELECT

                A.co_art, A.art_des, ISNULL(dbo.ArtUnidadBase(A.co_art, NEVR.co_uni, NEVR.total_art), 0) AS total_art,

                AU.co_uni, ISNULL(NEVR.total, 0) AS total, 0.00 AS total_entrada,

                NEVR.total * CASE WHEN ER.anulado = 1 THEN 0

                                  ELSE 1

                             END * -1 AS total_salida, AU2.co_uni AS co_uni_base, NEVR.co_alma,

                dbo.fechasimple(ER.fec_emis) AS fecha, NEVR.reng_num, NEVR.doc_num, ER.anulado AS anulado, '' co_prov,

                ER.co_cli, 'NDES' AS tipo,

				A.tipo AS tipo_art,

                ISNULL(NEVR.numero_lote, 'Por Asignar') AS numero_lote

              FROM

                saArticulo AS A

                LEFT JOIN ( SELECT

                                DVR.co_art, DVR.doc_num, DVR.co_uni, DVR.co_alma, DVR.reng_num, DEVR.total,

                                DVR.total_art, DVR.rowguid, DEVR.numero_lote

                            FROM

                                saNotaDespachoVentaReng AS DVR

                                INNER JOIN ( SELECT

                                                SUM(DEVR.total_art) AS total, DEVR.doc_num, DEVR.co_alma, DEVR.co_art,

                                                SL.numero_lote, DEVR.reng_num

                                             FROM

                                                saNotaDespachoVentaReng AS DEVR

                                                LEFT JOIN saLoteSalida AS SL ON DEVR.rowguid = SL.rowguid_reng

                                                                                AND DEVR.co_art = SL.co_art

                                                                                AND SL.tipo_doc = 'NDES'

-- 												LEFT JOIN saLoteEntrada AS SE ON SL.rowguid_lote = SE.rowguid



                                             GROUP BY

                                                DEVR.doc_num, DEVR.co_alma, DEVR.co_art, DEVR.reng_num, SL.numero_lote

                                           ) AS DEVR ON DVR.doc_num = DEVR.doc_num

                                                        AND DVR.co_alma = DEVR.co_alma

                                                        AND DVR.co_art = DEVR.co_art

                                                        AND DVR.reng_num = DEVR.reng_num

                          ) AS NEVR ON A.co_art = NEVR.co_art

                                       AND A.maneja_lote = 1

                INNER JOIN saNotaDespachoVenta ER ON NEVR.doc_num = ER.doc_num



                INNER JOIN saArtUnidad AS AU ON AU.co_art = NEVR.co_art

                                                AND au.co_uni = NEVR.co_uni

                LEFT JOIN saArtUnidad AS AU2 ON AU2.co_art = A.co_art

                                                AND AU2.uni_principal = 1

              WHERE

                ( @sCo_Art_d IS NULL

                  OR A.co_art >= @sCo_Art_d

                )

                AND ( @sCo_Art_h IS NULL

                      OR A.co_art <= @sCo_Art_h

                    )

                AND ( ( @dCo_fecha_d IS NULL

                        OR dbo.fechasimple(ER.fec_emis) >= @dCo_fecha_d

                      )

                      AND ( @dCo_fecha_h IS NULL

                            OR dbo.fechasimple(ER.fec_emis) <= @dCo_fecha_h

                          )

                    )

                AND ( @sCo_Almacen IS NULL

                      OR NEVR.co_alma = @sCo_Almacen

                    )

                AND ( @sCo_Linea_d IS NULL

                      OR A.co_lin >= @sCo_Linea_d

                    )

                AND ( @sCo_Linea_h IS NULL

                      OR A.co_lin <= @sCo_Linea_h

                    )

                AND ( @sCo_Categoria_d IS NULL

                      OR A.co_cat >= @sCo_Categoria_d

                    )

                AND ( @sCo_Categoria_h IS NULL

                      OR A.co_cat <= @sCo_Categoria_h

                    )

                AND ( @sNumero_Lote IS NULL

                      OR NEVR.numero_lote = @sNumero_Lote

                    )

                AND ( @sCo_Sucursal IS NULL

                      OR A.co_sucu_in = @sCo_Sucursal

                    )

              UNION ALL

--9.1 Traslado Salida Fec_sal

              SELECT

                A.co_art, A.art_des, ISNULL(dbo.ArtUnidadBase(A.co_art, TR.co_uni, TR.total_art), 0) AS total_art,

                TR.co_uni, ISNULL(TR.total, 0) AS total, 0.00 AS total_entrada,

                TR.total * CASE WHEN TS.anulado = 1 THEN 0

                                ELSE 1

                           END * -1 AS total_salida, AU2.co_uni AS co_uni_base, TS.alm_orig AS co_alma,

                dbo.fechasimple(TS.fec_sal) AS fecha, TR.reng_num, TR.tras_num, TS.anulado AS anulado, '' AS co_prov,

                '' AS co_cli, 'TRAS' AS tipo,

				A.tipo AS tipo_art,

                ISNULL(TR.numero_lote, 'Por Asignar') AS numero_lote

              FROM

                saArticulo AS A

                LEFT JOIN ( SELECT

                                DVR.co_art, DVR.tras_num, DVR.co_uni, DVR.reng_num, DEVR.total, DVR.total_art,

                                DVR.rowguid, DEVR.numero_lote

                            FROM

                                saTrasladoReng AS DVR

                                INNER JOIN saTraslado AS TR ON DVR.tras_num = TR.tras_num

                                INNER JOIN ( SELECT

                                                SUM(SL.cantidad) AS total, DEVR.tras_num, T.alm_orig, DEVR.co_art,

                                                SL.numero_lote, DEVR.reng_num

                                             FROM

                                                saTrasladoReng AS DEVR

                                                LEFT JOIN saLoteSalida AS SL ON DEVR.rowguid = SL.rowguid_reng

                                                                                AND DEVR.co_art = SL.co_art

                                                                                AND SL.tipo_doc = 'TRAS'

-- 												LEFT JOIN saLoteEntrada AS SE ON SL.rowguid_lote = SE.rowguid

                                                LEFT JOIN saTraslado AS T ON T.tras_num = DEVR.tras_num

                                             GROUP BY

                                                DEVR.tras_num, T.alm_orig, DEVR.co_art, DEVR.reng_num, SL.numero_lote

                                           ) AS DEVR ON DVR.tras_num = DEVR.tras_num

                                                        AND tr.alm_orig = DEVR.alm_orig

                                                        AND DVR.co_art = DEVR.co_art

                                                        AND DVR.reng_num = DEVR.reng_num

                          ) AS TR ON A.co_art = TR.co_art

                                     AND A.maneja_lote = 1

                INNER JOIN saTraslado TS ON TR.tras_num = TS.tras_num

                INNER JOIN saArtUnidad AS AU ON AU.co_art = TR.co_art

                                                AND AU.co_uni = TR.co_uni

                LEFT JOIN saArtUnidad AS AU2 ON AU2.co_art = A.co_art

                                                AND AU2.uni_principal = 1

              WHERE

                ( @sCo_Art_d IS NULL

                  OR A.co_art >= @sCo_Art_d

                )

                AND ( @sCo_Art_h IS NULL

                      OR A.co_art <= @sCo_Art_h

                    )

                AND ( ( @dCo_fecha_d IS NULL

                        OR dbo.fechasimple(TS.fec_sal) >= @dCo_fecha_d

                      )

                      AND ( @dCo_fecha_h IS NULL

                            OR dbo.fechasimple(TS.fec_sal) <= @dCo_fecha_h

                          )

                    )

                AND ( @sCo_Almacen IS NULL

                      OR TS.alm_orig = @sCo_Almacen

                    )

                AND ( @sCo_Linea_d IS NULL

                      OR A.co_lin >= @sCo_Linea_d

                    )

                AND ( @sCo_Linea_h IS NULL

                      OR A.co_lin <= @sCo_Linea_h

                    )

                AND ( @sCo_Categoria_d IS NULL

                      OR A.co_cat >= @sCo_Categoria_d

                    )

                AND ( @sCo_Categoria_h IS NULL

                      OR A.co_cat <= @sCo_Categoria_h

                    )

                AND ( @sNumero_Lote IS NULL

                      OR TR.numero_lote = @sNumero_Lote

                    )

                AND ( @sCo_Sucursal IS NULL

                      OR A.co_sucu_in = @sCo_Sucursal

                    )

              UNION ALL

--9.2 Traslado Entrada Fec_sal

              SELECT

                A.co_art, A.art_des, ISNULL(dbo.ArtUnidadBase(A.co_art, TR.co_uni, TR.total_art), 0) AS total_art,

                TR.co_uni, ISNULL(TR.total, 0) AS total, TR.total * CASE WHEN T.anulado = 1 THEN 0

                                                                         ELSE 1

                                                                    END AS total_entrada, 0.00 AS total_salida,

                AU2.co_uni AS co_uni_base, T.alm_tmp AS co_alma, dbo.fechasimple(T.fec_sal) AS fecha, TR.reng_num,

                TR.tras_num, T.anulado AS anulado, '' AS co_prov, '' AS co_cli, 'TRAE' AS tipo,



                A.tipo AS tipo_art, ISNULL(TR.numero_lote, 'Por Asignar') AS numero_lote

              FROM

                saArticulo AS A

                LEFT JOIN ( SELECT

                                DVR.co_art, DVR.tras_num, DVR.co_uni, DVR.reng_num, DEVR.total, DVR.total_art,

                                DVR.rowguid, DEVR.numero_lote

                            FROM

                                saTrasladoReng AS DVR

                                INNER JOIN saTraslado AS TR ON DVR.tras_num = TR.tras_num

                                INNER JOIN ( SELECT



                                                SUM(SL.cantidad) AS total, DEVR.tras_num, T.alm_tmp, DEVR.co_art,

                                                SL.numero_lote, DEVR.reng_num

                                             FROM

                                                saTrasladoReng AS DEVR

                                                LEFT JOIN saLoteEntrada AS SL ON DEVR.rowguid = SL.rowguid_reng

                                                                                 AND DEVR.co_art = SL.co_art

                                                                                 AND SL.tipo_doc = 'TRAS'

                                                LEFT JOIN saTraslado AS T ON T.tras_num = DEVR.tras_num





                                             GROUP BY

                                                DEVR.tras_num, T.alm_tmp, DEVR.co_art, DEVR.reng_num, SL.numero_lote

                                           ) AS DEVR ON DVR.tras_num = DEVR.tras_num

                                                        AND tr.alm_tmp = DEVR.alm_tmp

                                                        AND DVR.co_art = DEVR.co_art

                                                        AND DVR.reng_num = DEVR.reng_num

                          ) AS TR ON A.co_art = TR.co_art

                                     AND A.maneja_lote = 1

                INNER JOIN saTraslado T ON TR.tras_num = T.tras_num



                INNER JOIN saArtUnidad AS AU ON AU.co_art = TR.co_art

                                                AND AU.co_uni = TR.co_uni

                LEFT JOIN saArtUnidad AS AU2 ON AU2.co_art = A.co_art

                                                AND AU2.uni_principal = 1

              WHERE

                ( @sCo_Art_d IS NULL

                  OR A.co_art >= @sCo_Art_d

                )

                AND ( @sCo_Art_h IS NULL

                      OR A.co_art <= @sCo_Art_h

                    )

                AND ( ( @dCo_fecha_d IS NULL

                        OR dbo.fechasimple(T.fec_sal) >= @dCo_fecha_d

                      )

                      AND ( @dCo_fecha_h IS NULL

                            OR dbo.fechasimple(T.fec_sal) <= @dCo_fecha_h

                          )

                    )

                AND ( @sCo_Almacen IS NULL

                      OR T.alm_tmp = @sCo_Almacen

                    )

                AND ( @sCo_Linea_d IS NULL

                      OR A.co_lin >= @sCo_Linea_d

                    )

                AND ( @sCo_Linea_h IS NULL

                      OR A.co_lin <= @sCo_Linea_h

                    )

                AND ( @sCo_Categoria_d IS NULL

                      OR A.co_cat >= @sCo_Categoria_d

                    )

                AND ( @sCo_Categoria_h IS NULL

                      OR A.co_cat <= @sCo_Categoria_h

                    )

                AND ( @sNumero_Lote IS NULL

                      OR TR.numero_lote = @sNumero_Lote

                    )

                AND ( @sCo_Sucursal IS NULL

                      OR A.co_sucu_in = @sCo_Sucursal

                    )

              UNION ALL

--9.3 Traslado Temporal 2 Salida Fec_conf

              SELECT

                A.co_art, A.art_des, ISNULL(dbo.ArtUnidadBase(A.co_art, TR.co_uni, TR.total_art), 0) AS total_art,

                TR.co_uni, ISNULL(TR.total, 0) AS total, 0.00 AS total_entrada,

                TR.total * CASE WHEN T.anulado = 1 THEN 0

                                ELSE 1

                           END * -1 AS total_salida, AU2.co_uni AS co_uni_base, T.alm_tmp AS co_alma,

                dbo.fechasimple(T.fec_conf) AS fecha, TR.reng_num, TR.tras_num, T.anulado AS anulado, '' AS co_prov,

                '' AS co_cli, 'TRAS' AS tipo,

				A.tipo AS tipo_art,

                ISNULL(TR.numero_lote, 'Por Asignar') AS numero_lote

              FROM

                saArticulo AS A

                LEFT JOIN ( SELECT

                                DVR.co_art, DVR.tras_num, DVR.co_uni, DVR.reng_num, DEVR.total, DVR.total_art,

                                DVR.rowguid, DEVR.numero_lote

                            FROM

                                saTrasladoReng AS DVR

                                INNER JOIN saTraslado AS TR ON DVR.tras_num = TR.tras_num

                                INNER JOIN ( SELECT

--- Sit.#44212 (08/01/2018)-HZ:

                                                SUM(SL.cantidad) AS total, DEVR.tras_num, T.alm_tmp, DEVR.co_art,

                                                 SL.numero_lote, DEVR.reng_num

                                             FROM

                                                saTrasladoReng AS DEVR

                                                LEFT JOIN saLoteSalida AS SL ON DEVR.rowguid = SL.rowguid_reng

                                                                                AND DEVR.co_art = SL.co_art

                                                                                AND SL.tipo_doc = 'TRAS'

-- 												LEFT JOIN saLoteEntrada AS SE ON SL.rowguid_lote = SE.rowguid

                                                LEFT JOIN saTraslado AS T ON T.tras_num = DEVR.tras_num



--- Fin Sit.#44212 -12

                                             GROUP BY

                                                DEVR.tras_num, T.alm_tmp, DEVR.co_art, DEVR.reng_num, SL.numero_lote

                                           ) AS DEVR ON DVR.tras_num = DEVR.tras_num

                                                        AND tr.alm_tmp = DEVR.alm_tmp

                                                        AND DVR.co_art = DEVR.co_art

                                                        AND DVR.reng_num = DEVR.reng_num

                          ) AS TR ON A.co_art = TR.co_art

                                     AND A.maneja_lote = 1

                INNER JOIN saTraslado T ON TR.tras_num = T.tras_num

                                           AND T.confirma = 1

                INNER JOIN saArtUnidad AS AU ON AU.co_art = TR.co_art

                                                AND AU.co_uni = TR.co_uni

                LEFT JOIN saArtUnidad AS AU2 ON AU2.co_art = A.co_art

                                                AND AU2.uni_principal = 1

              WHERE

                ( @sCo_Art_d IS NULL

                  OR A.co_art >= @sCo_Art_d

                )

                AND ( @sCo_Art_h IS NULL

                      OR A.co_art <= @sCo_Art_h

                    )

                AND ( ( @dCo_fecha_d IS NULL

                        OR dbo.fechasimple(T.fec_conf) >= @dCo_fecha_d

                      )

                      AND ( @dCo_fecha_h IS NULL

                            OR dbo.fechasimple(T.fec_conf) <= @dCo_fecha_h

                          )

                    )

                AND ( @sCo_Almacen IS NULL

                      OR T.alm_tmp = @sCo_Almacen

                    )

                AND ( @sCo_Linea_d IS NULL

                      OR A.co_lin >= @sCo_Linea_d

                    )

                AND ( @sCo_Linea_h IS NULL

                      OR A.co_lin <= @sCo_Linea_h

                    )

                AND ( @sCo_Categoria_d IS NULL

                      OR A.co_cat >= @sCo_Categoria_d

                    )

                AND ( @sCo_Categoria_h IS NULL

                      OR A.co_cat <= @sCo_Categoria_h

                    )

                AND ( @sNumero_Lote IS NULL

                      OR TR.numero_lote = @sNumero_Lote

                    )

                AND ( @sCo_Sucursal IS NULL

                      OR A.co_sucu_in = @sCo_Sucursal

                    )

              UNION ALL

--9.4 Traslado Entrada Destino

              SELECT

                A.co_art, A.art_des, ISNULL(dbo.ArtUnidadBase(A.co_art, TR.co_uni, TR.total_art), 0) AS total_art,

                TR.co_uni, ISNULL(TR.total, 0) AS total, TR.total * CASE WHEN T.anulado = 1 THEN 0

                                                                         ELSE 1

                                                                    END AS total_entrada, 0.00 AS total_salida,

                AU2.co_uni AS co_uni_base, T.alm_dest AS co_alma, dbo.fechasimple(T.fec_conf) AS fecha, TR.reng_num,

                TR.tras_num, T.anulado AS anulado, '' AS co_prov, '' AS co_cli, 'TRAE' AS tipo,

                A.tipo AS tipo_art, ISNULL(TR.numero_lote, 'Por Asignar') AS numero_lote

              FROM

                saArticulo AS A

                LEFT JOIN ( SELECT

                                DVR.co_art, DVR.tras_num, DVR.co_uni, DVR.reng_num, DEVR.total, DVR.total_art,

                                DVR.rowguid, DEVR.numero_lote

                            FROM

                                saTrasladoReng AS DVR

                                INNER JOIN saTraslado AS TR ON DVR.tras_num = TR.tras_num

                                INNER JOIN ( SELECT



                                                SUM(SL.cantidad) AS total, DEVR.tras_num, T.alm_dest, DEVR.co_art,

                                                SL.numero_lote, DEVR.reng_num

                                             FROM

                                                saTrasladoReng AS DEVR

                                                LEFT JOIN saLoteEntrada AS SL ON DEVR.rowguid = SL.rowguid_reng

                                                                                 AND DEVR.co_art = SL.co_art

                                                                                 AND SL.tipo_doc = 'TRAS'

                                                LEFT JOIN saTraslado AS T ON T.tras_num = DEVR.tras_num



                                             GROUP BY

                                                DEVR.tras_num, T.alm_dest, DEVR.co_art, DEVR.reng_num, SL.numero_lote

                                           ) AS DEVR ON DVR.tras_num = DEVR.tras_num

                                                        AND tr.alm_dest = DEVR.alm_dest

                                                        AND DVR.co_art = DEVR.co_art

                                                        AND DVR.reng_num = DEVR.reng_num

                          ) AS TR ON A.co_art = TR.co_art

                                     AND A.maneja_lote = 1

                INNER JOIN saTraslado T ON TR.tras_num = T.tras_num

                                           AND T.confirma = 1

                INNER JOIN saArtUnidad AS AU ON AU.co_art = TR.co_art

                                                AND AU.co_uni = TR.co_uni

                LEFT JOIN saArtUnidad AS AU2 ON AU2.co_art = A.co_art

                                                AND AU2.uni_principal = 1

              WHERE

                ( @sCo_Art_d IS NULL

                  OR A.co_art >= @sCo_Art_d

                )

                AND ( @sCo_Art_h IS NULL

                      OR A.co_art <= @sCo_Art_h

                    )

                AND ( ( @dCo_fecha_d IS NULL

                        OR dbo.fechasimple(T.fec_conf) >= @dCo_fecha_d

                      )

                      AND ( @dCo_fecha_h IS NULL

                            OR dbo.fechasimple(T.fec_conf) <= @dCo_fecha_h

                          )

                    )

                AND ( @sCo_Almacen IS NULL

                      OR T.alm_dest = @sCo_Almacen

                    )

                AND ( @sCo_Linea_d IS NULL

                      OR A.co_lin >= @sCo_Linea_d

                    )

                AND ( @sCo_Linea_h IS NULL

                      OR A.co_lin <= @sCo_Linea_h

                    )

                AND ( @sCo_Categoria_d IS NULL

                      OR A.co_cat >= @sCo_Categoria_d

                    )

                AND ( @sCo_Categoria_h IS NULL

                      OR A.co_cat <= @sCo_Categoria_h

                    )

                AND ( @sNumero_Lote IS NULL

                      OR TR.numero_lote = @sNumero_Lote

                    )

                AND ( @sCo_Sucursal IS NULL

                      OR A.co_sucu_in = @sCo_Sucursal

                    )

            ) A

            INNER JOIN ( SELECT

                            AR.co_Art,

                            SUM(dbo.ConsultarStockActualxAlmacenxFechaxLote(AR.co_Art, @sCo_Almacen,

                                                                            DATEADD(ss, -1, @dCo_fecha_d), NULL,

                                                                            @sCo_Movimiento, @sNumero_Lote)) AS StockInic,

                            SUM(dbo.ConsultarStockActualxAlmacenxFechaxLote(AR.co_Art, @sCo_Almacen, @dCo_fecha_h, NULL,

                                                                            @sCo_Movimiento, @sNumero_Lote)) AS StockFinal

                         FROM

                            saArticulo AR

                         GROUP BY

                            AR.co_Art

                       ) B ON B.co_art = A.co_art

        WHERE

            ( @sCo_Movimiento IS NULL

              OR @sCo_Movimiento = A.tipo

            )

            AND ( ( @sAsignacion = '5' )

                  OR ( @sAsignacion = '1'

                       AND A.total_art - A.total = 0

                     )

                  OR ( @sAsignacion = '2'

                       AND ( A.total_art - A.total > 0

                             AND A.total_art <> A.total

                           )

                     )

                  OR ( @sAsignacion = '3'

                       AND A.numero_lote = 'Por Asignar'

                     )

                  OR ( @sAsignacion = '4'

                       AND ( ( A.total_art - A.total = 0 )

                             OR ( A.total_art <> A.total )

                             AND A.numero_lote <> 'Por Asignar'

                           )

                     )

                )

            AND A.tipo_art <> 'S'

        ORDER BY

            A.co_art, A.fecha, A.tipo, A.doc_num

    END