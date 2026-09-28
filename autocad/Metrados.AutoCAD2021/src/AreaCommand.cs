using System;
using System.Collections.Generic;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Geometry;
using Autodesk.AutoCAD.Runtime;

namespace Metrados.AutoCAD2021
{
    public sealed partial class Commands
    {
        private const double EndpointTolerance = 0.0000001;

        private enum MeasurementMode
        {
            Total,
            Individual,
            Layer
        }

        private sealed class AreaValue
        {
            internal double RawArea { get; set; }
            internal int EntityCount { get; set; }
            internal string Layer { get; set; }
        }

        [CommandMethod("MTRAREA", CommandFlags.Modal | CommandFlags.UsePickSet)]
        public void MeasureArea()
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
                editor.WriteMessage("\nMTRAREA: define las unidades métricas del dibujo con UNITS " +
                                    "(milímetros, centímetros o metros) antes de medir.");
                return;
            }

            MeasurementMode mode;
            if (!TryPromptMeasurementMode(editor, out mode))
            {
                return;
            }

            PromptSelectionOptions options = new PromptSelectionOptions();
            options.MessageForAdding = "\nSeleccione líneas, polilíneas, círculos o elipses cerradas: ";
            options.MessageForRemoval = "\nQuite objetos de la selección: ";
            PromptSelectionResult selected = editor.GetSelection(options, CurveSelectionFilter());
            if (selected.Status != PromptStatus.OK || selected.Value.Count == 0)
            {
                return;
            }

            List<AreaValue> values;
            string geometryError;
            if (!TryCalculateAreaValues(document.Database, selected.Value.GetObjectIds(),
                                        mode == MeasurementMode.Layer,
                                        out values, out geometryError))
            {
                editor.WriteMessage("\nMTRAREA: " + geometryError);
                return;
            }

            string commonName = string.Empty;
            if (mode != MeasurementMode.Layer &&
                !TryPromptName(editor, "\nNombre del área: ", "MTRAREA", out commonName))
            {
                return;
            }

            MeasurementPayload payload = new MeasurementPayload
            {
                DrawingUnit = unitLabel,
                EntityCount = selected.Value.Count,
                Drawing = document.Name ?? string.Empty
            };
            double scale = metersPerUnit * metersPerUnit;
            double total = 0.0;
            if (mode == MeasurementMode.Total)
            {
                foreach (AreaValue value in values)
                {
                    total += value.RawArea * scale;
                }
                if (!ValidPositive(total))
                {
                    editor.WriteMessage("\nMTRAREA: el área calculada no es válida.");
                    return;
                }
                payload.Name = commonName;
                payload.AreaSquareMeters = total;
                payload.RawArea = total / scale;
                payload.RegionCount = values.Count;
            }
            else
            {
                payload.Measurements = new List<MeasurementEntry>();
                foreach (AreaValue value in values)
                {
                    double area = value.RawArea * scale;
                    string name = mode == MeasurementMode.Layer ? value.Layer : commonName;
                    if (!ValidPositive(area) || !ValidAutomaticName(name))
                    {
                        editor.WriteMessage("\nMTRAREA: una medición o nombre de layer no es válido.");
                        return;
                    }
                    total += area;
                    payload.Measurements.Add(new MeasurementEntry
                    {
                        Name = name,
                        AreaSquareMeters = area,
                        EntityCount = value.EntityCount,
                        RegionCount = 1
                    });
                }
            }

            string message;
            bool sent = Plugin.Bridge.SendArea(payload, out message);
            editor.WriteMessage("\nMTRAREA: " + message);
            if (sent)
            {
                editor.WriteMessage(" " + (mode == MeasurementMode.Total
                    ? "Área total: " + total.ToString("0.00") + " m²."
                    : payload.Measurements.Count + " áreas agregadas; total: " +
                      total.ToString("0.00") + " m²."));
            }
        }

        private static SelectionFilter CurveSelectionFilter()
        {
            return new SelectionFilter(new TypedValue[]
            {
                new TypedValue((int)DxfCode.Operator, "<OR"),
                new TypedValue((int)DxfCode.Start, "LINE"),
                new TypedValue((int)DxfCode.Start, "LWPOLYLINE"),
                new TypedValue((int)DxfCode.Start, "POLYLINE"),
                new TypedValue((int)DxfCode.Start, "CIRCLE"),
                new TypedValue((int)DxfCode.Start, "ELLIPSE"),
                new TypedValue((int)DxfCode.Operator, "OR>")
            });
        }

        private static bool TryPromptMeasurementMode(Editor editor, out MeasurementMode mode)
        {
            mode = MeasurementMode.Total;
            PromptKeywordOptions options = new PromptKeywordOptions(
                "\nResultado [Total/Individual/Layer] <Total>: ");
            options.AllowNone = true;
            options.Keywords.Add("Total");
            options.Keywords.Add("Individual");
            options.Keywords.Add("Layer");
            PromptResult result = editor.GetKeywords(options);
            if (result.Status == PromptStatus.None)
            {
                return true;
            }
            if (result.Status != PromptStatus.OK)
            {
                return false;
            }
            if (string.Equals(result.StringResult, "Individual", StringComparison.OrdinalIgnoreCase))
            {
                mode = MeasurementMode.Individual;
            }
            else if (string.Equals(result.StringResult, "Layer", StringComparison.OrdinalIgnoreCase))
            {
                mode = MeasurementMode.Layer;
            }
            return true;
        }

        private static bool TryPromptName(Editor editor, string prompt, string command,
                                          out string name)
        {
            name = string.Empty;
            PromptStringOptions options = new PromptStringOptions(prompt);
            options.AllowSpaces = true;
            PromptResult result = editor.GetString(options);
            if (result.Status != PromptStatus.OK)
            {
                return false;
            }
            name = (result.StringResult ?? string.Empty).Trim();
            if (name.Length == 0)
            {
                editor.WriteMessage("\n" + command + ": escribe un nombre antes de enviar la medición.");
                return false;
            }
            if (name.Length > 200)
            {
                editor.WriteMessage("\n" + command + ": el nombre admite hasta 200 caracteres.");
                return false;
            }
            return true;
        }

        private static bool ValidAutomaticName(string name)
        {
            return !string.IsNullOrWhiteSpace(name) && name.Trim().Length <= 200;
        }

        private static bool ValidPositive(double value)
        {
            return !double.IsNaN(value) && !double.IsInfinity(value) && value > 0.0;
        }

        private static bool TryCalculateAreaValues(Database database, ObjectId[] ids,
                                                   bool splitLinesByLayer,
                                                   out List<AreaValue> values,
                                                   out string error)
        {
            values = new List<AreaValue>();
            error = string.Empty;
            Dictionary<string, DBObjectCollection> lineGroups =
                new Dictionary<string, DBObjectCollection>(StringComparer.OrdinalIgnoreCase);
            Dictionary<string, Dictionary<PointKey, int>> endpointGroups =
                new Dictionary<string, Dictionary<PointKey, int>>(StringComparer.OrdinalIgnoreCase);
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
                        Line line = curve as Line;
                        if (line != null)
                        {
                            if (line.Length <= EndpointTolerance)
                            {
                                error = "la selección contiene una línea sin longitud.";
                                return false;
                            }
                            string key = splitLinesByLayer ? line.Layer : string.Empty;
                            DBObjectCollection lines;
                            Dictionary<PointKey, int> endpoints;
                            if (!lineGroups.TryGetValue(key, out lines))
                            {
                                lines = new DBObjectCollection();
                                endpoints = new Dictionary<PointKey, int>();
                                lineGroups.Add(key, lines);
                                endpointGroups.Add(key, endpoints);
                            }
                            else
                            {
                                endpoints = endpointGroups[key];
                            }
                            lines.Add(line);
                            Increment(endpoints, new PointKey(line.StartPoint));
                            Increment(endpoints, new PointKey(line.EndPoint));
                            continue;
                        }
                        if (!(curve is Polyline) && !(curve is Polyline2d) &&
                            !(curve is Circle) && !(curve is Ellipse))
                        {
                            error = "solo se admiten líneas, polilíneas 2D, círculos y elipses.";
                            return false;
                        }
                        if (!curve.Closed)
                        {
                            error = "todas las polilíneas y elipses deben estar cerradas.";
                            return false;
                        }
                        double area = Math.Abs(curve.Area);
                        if (!ValidPositive(area))
                        {
                            error = "uno de los contornos no tiene un área válida.";
                            return false;
                        }
                        values.Add(new AreaValue
                        {
                            RawArea = area,
                            EntityCount = 1,
                            Layer = curve.Layer
                        });
                    }

                    foreach (KeyValuePair<string, DBObjectCollection> group in lineGroups)
                    {
                        foreach (KeyValuePair<PointKey, int> endpoint in endpointGroups[group.Key])
                        {
                            if (endpoint.Value != 2)
                            {
                                error = splitLinesByLayer
                                    ? "las líneas deben formar contornos cerrados dentro de cada layer."
                                    : "las líneas seleccionadas deben formar uno o varios contornos cerrados, sin extremos sueltos.";
                                return false;
                            }
                        }
                        DBObjectCollection regions = Region.CreateFromCurves(group.Value);
                        try
                        {
                            if (regions.Count == 0)
                            {
                                error = "las líneas seleccionadas no forman un contorno plano cerrado.";
                                return false;
                            }
                            foreach (DBObject item in regions)
                            {
                                Region region = item as Region;
                                if (region == null || !ValidPositive(region.Area))
                                {
                                    error = "las líneas seleccionadas producen una región inválida.";
                                    return false;
                                }
                                values.Add(new AreaValue
                                {
                                    RawArea = Math.Abs(region.Area),
                                    EntityCount = group.Value.Count,
                                    Layer = group.Key
                                });
                            }
                        }
                        finally
                        {
                            foreach (DBObject item in regions)
                            {
                                item.Dispose();
                            }
                        }
                    }
                    transaction.Commit();
                }
            }
            catch (Autodesk.AutoCAD.Runtime.Exception)
            {
                error = "los objetos deben ser planos, cerrados y no ambiguos.";
                return false;
            }
            catch (OverflowException)
            {
                error = "las coordenadas del dibujo están fuera del rango admitido.";
                return false;
            }
            return values.Count > 0;
        }

        private static void Increment(Dictionary<PointKey, int> values, PointKey point)
        {
            int count;
            values.TryGetValue(point, out count);
            values[point] = count + 1;
        }

        private static bool MetricScale(UnitsValue units, out double metersPerUnit, out string label)
        {
            switch ((int)units)
            {
                case 4:
                    metersPerUnit = 0.001;
                    label = "mm";
                    return true;
                case 5:
                    metersPerUnit = 0.01;
                    label = "cm";
                    return true;
                case 6:
                    metersPerUnit = 1.0;
                    label = "m";
                    return true;
                case 7:
                    metersPerUnit = 1000.0;
                    label = "km";
                    return true;
                default:
                    metersPerUnit = 0.0;
                    label = string.Empty;
                    return false;
            }
        }

        private struct PointKey : IEquatable<PointKey>
        {
            private readonly long x;
            private readonly long y;
            private readonly long z;

            internal PointKey(Point3d point)
            {
                x = Quantize(point.X);
                y = Quantize(point.Y);
                z = Quantize(point.Z);
            }

            private static long Quantize(double value)
            {
                double scaled = Math.Round(value / EndpointTolerance);
                if (scaled > long.MaxValue || scaled < long.MinValue)
                {
                    throw new OverflowException();
                }
                return (long)scaled;
            }

            public bool Equals(PointKey other)
            {
                return x == other.x && y == other.y && z == other.z;
            }

            public override bool Equals(object value)
            {
                return value is PointKey && Equals((PointKey)value);
            }

            public override int GetHashCode()
            {
                unchecked
                {
                    int hash = x.GetHashCode();
                    hash = (hash * 397) ^ y.GetHashCode();
                    return (hash * 397) ^ z.GetHashCode();
                }
            }
        }
    }
}
