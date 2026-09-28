using System;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;

namespace Metrados.AutoCAD2021
{
    public sealed partial class Commands
    {
        [CommandMethod("MTRACERO", CommandFlags.Modal)]
        public void MeasureDistributedSteel()
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
                editor.WriteMessage("\nMTRACERO: define las unidades métricas del dibujo con UNITS " +
                                    "(milímetros, centímetros o metros) antes de medir.");
                return;
            }

            double rawLength;
            if (!TryGetDistance(editor,
                    "\nLargo de cada barra: indique dos puntos o escriba una distancia: ",
                    out rawLength))
            {
                return;
            }
            double rawDistribution;
            if (!TryGetDistance(editor,
                    "\nDistancia donde se distribuye el acero: indique dos puntos o escriba una distancia: ",
                    out rawDistribution))
            {
                return;
            }

            PromptEntityOptions textOptions = new PromptEntityOptions(
                "\nSeleccione el texto de distribución del acero: ");
            textOptions.SetRejectMessage("\nSeleccione un texto simple o texto múltiple.");
            textOptions.AddAllowedClass(typeof(DBText), true);
            textOptions.AddAllowedClass(typeof(MText), true);
            PromptEntityResult textResult = editor.GetEntity(textOptions);
            if (textResult.Status != PromptStatus.OK)
            {
                return;
            }

            string distributionText;
            using (Transaction transaction = document.Database.TransactionManager.StartOpenCloseTransaction())
            {
                DBObject value = transaction.GetObject(textResult.ObjectId, OpenMode.ForRead, false);
                DBText simple = value as DBText;
                MText multiple = value as MText;
                distributionText = simple != null ? simple.TextString :
                    (multiple != null ? multiple.Text : string.Empty);
                transaction.Commit();
            }
            distributionText = (distributionText ?? string.Empty).Trim();
            if (distributionText.Length == 0 || distributionText.Length > 500)
            {
                editor.WriteMessage("\nMTRACERO: el texto seleccionado está vacío o es demasiado largo.");
                return;
            }

            string description;
            if (!TryPromptName(editor, "\nDescripción del detalle de acero: ",
                               "MTRACERO", out description))
            {
                return;
            }

            double lengthMeters = rawLength * metersPerUnit;
            double distributionMeters = rawDistribution * metersPerUnit;
            if (!ValidPositive(lengthMeters) || !ValidPositive(distributionMeters))
            {
                editor.WriteMessage("\nMTRACERO: las distancias calculadas no son válidas.");
                return;
            }

            MeasurementPayload payload = new MeasurementPayload
            {
                Description = description,
                LengthMeters = lengthMeters,
                DistributionMeters = distributionMeters,
                DistributionText = distributionText,
                DrawingUnit = unitLabel,
                Drawing = document.Name ?? string.Empty
            };
            string message;
            bool sent = Plugin.Bridge.SendSteel(payload, out message);
            editor.WriteMessage("\nMTRACERO: " + message);
            if (sent)
            {
                editor.WriteMessage(" Largo: " + lengthMeters.ToString("0.00") +
                                    " m; distribución: " + distributionMeters.ToString("0.00") + " m.");
            }
        }

        private static bool TryGetDistance(Editor editor, string message, out double value)
        {
            value = 0.0;
            PromptDistanceOptions options = new PromptDistanceOptions(message);
            options.AllowNegative = false;
            options.AllowZero = false;
            PromptDoubleResult result = editor.GetDistance(options);
            if (result.Status != PromptStatus.OK)
            {
                return false;
            }
            value = result.Value;
            return ValidPositive(value);
        }
    }
}
