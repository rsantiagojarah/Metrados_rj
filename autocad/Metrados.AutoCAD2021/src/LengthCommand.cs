using System;
using System.Collections.Generic;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;

namespace Metrados.AutoCAD2021
{
    public sealed partial class Commands
    {
        private sealed class LengthValue
        {
            internal double RawLength { get; set; }
            internal string Layer { get; set; }
        }

        [CommandMethod("MTRLONGITUD", CommandFlags.Modal | CommandFlags.UsePickSet)]
        public void MeasureLength()
        {
            Document document = Application.DocumentManager.MdiActiveDocument;
            if (document == null)
            {
                return;
            }
            Editor editor = document.Editor;
            if (Plugin.Bridge == null)
            {
                editor.WriteMessage("\nLa conexión de Metrados no está inicializada.");
                return;
            }

            double metersPerUnit;
            string unitLabel;
            if (!MetricScale(document.Database.Insunits, out metersPerUnit, out unitLabel))
            {
                editor.WriteMessage("\nMTRLONGITUD: define las unidades métricas del dibujo con UNITS " +
                                    "(milímetros, centímetros o metros) antes de medir.");
                return;
            }

            MeasurementMode mode;
            if (!TryPromptMeasurementMode(editor, out mode))
            {
                return;
            }

            PromptSelectionOptions options = new PromptSelectionOptions();
            options.MessageForAdding = "\nSeleccione líneas, polilíneas, círculos o elipses: ";
            options.MessageForRemoval = "\nQuite objetos de la selección: ";
            PromptSelectionResult selected = editor.GetSelection(options, CurveSelectionFilter());
            if (selected.Status != PromptStatus.OK || selected.Value.Count == 0)
            {
                return;
            }

            List<LengthValue> values;
            string geometryError;
            if (!TryCalculateLengthValues(document.Database, selected.Value.GetObjectIds(),
                                          out values, out geometryError))
            {
                editor.WriteMessage("\nMTRLONGITUD: " + geometryError);
                return;
            }

            string commonName = string.Empty;
            if (mode != MeasurementMode.Layer &&
                !TryPromptName(editor, "\nNombre de la longitud o perímetro: ",
                               "MTRLONGITUD", out commonName))
            {
                return;
            }

            MeasurementPayload payload = new MeasurementPayload
            {
                DrawingUnit = unitLabel,
                EntityCount = selected.Value.Count,
                Drawing = document.Name ?? string.Empty
            };
            double total = 0.0;
            if (mode == MeasurementMode.Total)
            {
                foreach (LengthValue value in values)
                {
                    total += value.RawLength * metersPerUnit;
                }
                if (!ValidPositive(total))
                {
                    editor.WriteMessage("\nMTRLONGITUD: la longitud calculada no es válida.");
                    return;
                }
                payload.Name = commonName;
                payload.LengthMeters = total;
                payload.RawLength = total / metersPerUnit;
            }
            else
            {
                payload.Measurements = new List<MeasurementEntry>();
                foreach (LengthValue value in values)
                {
                    double length = value.RawLength * metersPerUnit;
                    string name = mode == MeasurementMode.Layer ? value.Layer : commonName;
                    if (!ValidPositive(length) || !ValidAutomaticName(name))
                    {
                        editor.WriteMessage("\nMTRLONGITUD: una medición o nombre de layer no es válido.");
                        return;
                    }
                    total += length;
                    payload.Measurements.Add(new MeasurementEntry
                    {
                        Name = name,
                        LengthMeters = length,
                        EntityCount = 1
                    });
                }
            }

            string message;
            bool sent = Plugin.Bridge.SendLength(payload, out message);
            editor.WriteMessage("\nMTRLONGITUD: " + message);
            if (sent)
            {
                editor.WriteMessage(" " + (mode == MeasurementMode.Total
                    ? "Longitud total: " + total.ToString("0.00") + " m."
                    : payload.Measurements.Count + " longitudes agregadas; total: " +
                      total.ToString("0.00") + " m."));
            }
        }

        private static bool TryCalculateLengthValues(Database database, ObjectId[] ids,
                                                     out List<LengthValue> values,
                                                     out string error)
        {
            values = new List<LengthValue>();
            error = string.Empty;
            try
            {
                using (Transaction transaction = database.TransactionManager.StartOpenCloseTransaction())
                {
                    foreach (ObjectId id in ids)
                    {
                        Curve curve = transaction.GetObject(id, OpenMode.ForRead, false) as Curve;
                        if (curve == null)
                        {
                            error = "la selección contiene un objeto no compatible.";
                            return false;
                        }
                        double start = curve.GetDistanceAtParameter(curve.StartParam);
                        double end = curve.GetDistanceAtParameter(curve.EndParam);
                        double length = Math.Abs(end - start);
                        if (!ValidPositive(length))
                        {
                            error = "uno de los objetos no tiene una longitud válida.";
                            return false;
                        }
                        values.Add(new LengthValue
                        {
                            RawLength = length,
                            Layer = curve.Layer
                        });
                    }
                    transaction.Commit();
                }
            }
            catch (Autodesk.AutoCAD.Runtime.Exception)
            {
                error = "no se pudo calcular la longitud de todos los objetos seleccionados.";
                return false;
            }
            return values.Count > 0;
        }
    }
}
