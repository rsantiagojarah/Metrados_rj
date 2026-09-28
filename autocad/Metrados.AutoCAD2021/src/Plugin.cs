using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;

[assembly: ExtensionApplication(typeof(Metrados.AutoCAD2021.Plugin))]
[assembly: CommandClass(typeof(Metrados.AutoCAD2021.Commands))]

namespace Metrados.AutoCAD2021
{
    public sealed class Plugin : IExtensionApplication
    {
        internal static MetradosBridgeClient Bridge { get; private set; }

        public void Initialize()
        {
            Bridge = new MetradosBridgeClient("AutoCAD 2021 / R24.0", true);
        }

        public void Terminate()
        {
            if (Bridge != null)
            {
                Bridge.Dispose();
                Bridge = null;
            }
        }
    }

    public sealed partial class Commands
    {
        [CommandMethod("MTRCONEXION", CommandFlags.Modal | CommandFlags.NoHistory)]
        public void ConnectionStatus()
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
            string message;
            bool connected = Plugin.Bridge.PingNow(out message);
            editor.WriteMessage("\n" + (connected ? "Metrados: " : "Metrados — sin conexión: ") + message);
        }
    }
}
