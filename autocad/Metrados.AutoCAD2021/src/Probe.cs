using System;
using System.Collections.Generic;
using System.Threading;

namespace Metrados.AutoCAD2021
{
    internal static class Probe
    {
        private static int Main(string[] arguments)
        {
            using (MetradosBridgeClient client = new MetradosBridgeClient("probe", false))
            {
                string message;
                bool connected = client.PingNow(out message);
                Console.WriteLine(message);
                Console.Out.Flush();
                if (!connected)
                {
                    return 1;
                }
                if (arguments.Length > 0 && arguments[0] == "--area")
                {
                    connected = client.SendArea(new MeasurementPayload
                    {
                        Name = "ÁREA DE PRUEBA",
                        AreaSquareMeters = 12.5,
                        RawArea = 12.5,
                        DrawingUnit = "m",
                        EntityCount = 2,
                        RegionCount = 1,
                        Drawing = "probe.dwg"
                    }, out message);
                    Console.WriteLine(message);
                    return connected ? 0 : 1;
                }
                if (arguments.Length > 0 && arguments[0] == "--area-batch")
                {
                    connected = client.SendArea(new MeasurementPayload
                    {
                        DrawingUnit = "m",
                        EntityCount = 2,
                        Drawing = "probe.dwg",
                        Measurements = new List<MeasurementEntry>
                        {
                            new MeasurementEntry
                            {
                                Name = "A-PISOS",
                                AreaSquareMeters = 12.5,
                                EntityCount = 1,
                                RegionCount = 1
                            },
                            new MeasurementEntry
                            {
                                Name = "A-VEREDA",
                                AreaSquareMeters = 7.25,
                                EntityCount = 1,
                                RegionCount = 1
                            }
                        }
                    }, out message);
                    Console.WriteLine(message);
                    return connected ? 0 : 1;
                }
                if (arguments.Length > 0 && arguments[0] == "--length")
                {
                    connected = client.SendLength(new MeasurementPayload
                    {
                        Name = "LONGITUD DE PRUEBA",
                        LengthMeters = 8.75,
                        RawLength = 8.75,
                        DrawingUnit = "m",
                        EntityCount = 3,
                        Drawing = "probe.dwg"
                    }, out message);
                    Console.WriteLine(message);
                    return connected ? 0 : 1;
                }
                if (arguments.Length > 0 && arguments[0] == "--length-batch")
                {
                    connected = client.SendLength(new MeasurementPayload
                    {
                        DrawingUnit = "m",
                        EntityCount = 2,
                        Drawing = "probe.dwg",
                        Measurements = new List<MeasurementEntry>
                        {
                            new MeasurementEntry
                            {
                                Name = "CERCO",
                                LengthMeters = 10.125,
                                EntityCount = 1
                            },
                            new MeasurementEntry
                            {
                                Name = "A-MUROS",
                                LengthMeters = 4.445,
                                EntityCount = 1
                            }
                        }
                    }, out message);
                    Console.WriteLine(message);
                    return connected ? 0 : 1;
                }
                if (arguments.Length > 0 && arguments[0] == "--steel")
                {
                    connected = client.SendSteel(new MeasurementPayload
                    {
                        Description = "ACERO DE PRUEBA",
                        LengthMeters = 8.5,
                        DistributionMeters = 2.0,
                        DistributionText = "1Ø1/2\"@.20",
                        DrawingUnit = "m",
                        Drawing = "probe.dwg"
                    }, out message);
                    Console.WriteLine(message);
                    return connected ? 0 : 1;
                }
                if (arguments.Length == 0 || arguments[0] != "--reconnect")
                {
                    return 0;
                }
                Thread.Sleep(3000);
                connected = client.PingNow(out message);
                Console.WriteLine(message);
                return connected ? 0 : 1;
            }
        }
    }
}
