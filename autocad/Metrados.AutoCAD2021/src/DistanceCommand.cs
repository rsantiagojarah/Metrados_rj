using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;

namespace Metrados.AutoCAD2021
{
    public sealed partial class Commands
    {
        [CommandMethod("MTRDISTANCIA", CommandFlags.Modal)]
        public void SendPointDistance()
        {
            Document document = Application.DocumentManager.MdiActiveDocument;
            if (document == null || Plugin.Bridge == null) return;
            Editor editor = document.Editor;
            double metersPerUnit; string unitLabel;
            if (!MetricScale(document.Database.Insunits, out metersPerUnit, out unitLabel))
            {
                editor.WriteMessage("\nMTRDISTANCIA: define las unidades métricas del dibujo con UNITS.");
                return;
            }
            PromptPointResult first = editor.GetPoint("\nPrimer punto: ");
            if (first.Status != PromptStatus.OK) return;
            PromptPointOptions options = new PromptPointOptions("\nSegundo punto: ");
            options.BasePoint = first.Value; options.UseBasePoint = true;
            PromptPointResult second = editor.GetPoint(options);
            if (second.Status != PromptStatus.OK) return;
            double length = first.Value.DistanceTo(second.Value) * metersPerUnit;
            if (!ValidPositive(length)) { editor.WriteMessage("\nMTRDISTANCIA: la distancia no es válida."); return; }
            string message;
            bool sent = Plugin.Bridge.SendPointDistance(new MeasurementPayload {
                LengthMeters = length, DrawingUnit = unitLabel, Drawing = document.Name ?? string.Empty }, out message);
            editor.WriteMessage("\nMTRDISTANCIA: " + message);
        }
    }
}
