using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace Metrados.AutoCAD2021
{
    [DataContract]
    internal sealed class SessionDescriptor
    {
        [DataMember(Name = "protocol")]
        public int Protocol { get; set; }

        [DataMember(Name = "pipe")]
        public string Pipe { get; set; }

        [DataMember(Name = "token")]
        public string Token { get; set; }

        [DataMember(Name = "server_pid")]
        public int ServerProcessId { get; set; }

        [DataMember(Name = "session_id")]
        public string SessionId { get; set; }
    }

    [DataContract]
    internal sealed class ClientIdentity
    {
        [DataMember(Name = "name")]
        public string Name { get; set; }

        [DataMember(Name = "version")]
        public string Version { get; set; }

        [DataMember(Name = "process_id")]
        public int ProcessId { get; set; }

        [DataMember(Name = "autocad_release")]
        public string AutoCadRelease { get; set; }
    }

    [DataContract]
    internal sealed class MeasurementEntry
    {
        [DataMember(Name = "name")]
        public string Name { get; set; }

        [DataMember(Name = "area_m2", EmitDefaultValue = false)]
        public double AreaSquareMeters { get; set; }

        [DataMember(Name = "length_m", EmitDefaultValue = false)]
        public double LengthMeters { get; set; }

        [DataMember(Name = "entity_count")]
        public int EntityCount { get; set; }

        [DataMember(Name = "region_count", EmitDefaultValue = false)]
        public int RegionCount { get; set; }
    }

    [DataContract]
    internal sealed class MeasurementPayload
    {
        [DataMember(Name = "name")]
        public string Name { get; set; }

        [DataMember(Name = "area_m2")]
        public double AreaSquareMeters { get; set; }

        [DataMember(Name = "raw_area")]
        public double RawArea { get; set; }

        [DataMember(Name = "drawing_unit")]
        public string DrawingUnit { get; set; }

        [DataMember(Name = "entity_count")]
        public int EntityCount { get; set; }

        [DataMember(Name = "region_count")]
        public int RegionCount { get; set; }

        [DataMember(Name = "drawing")]
        public string Drawing { get; set; }

        [DataMember(Name = "length_m", EmitDefaultValue = false)]
        public double LengthMeters { get; set; }

        [DataMember(Name = "raw_length", EmitDefaultValue = false)]
        public double RawLength { get; set; }

        [DataMember(Name = "measurements", EmitDefaultValue = false)]
        public List<MeasurementEntry> Measurements { get; set; }

        [DataMember(Name = "description", EmitDefaultValue = false)]
        public string Description { get; set; }

        [DataMember(Name = "distribution_m", EmitDefaultValue = false)]
        public double DistributionMeters { get; set; }

        [DataMember(Name = "distribution_text", EmitDefaultValue = false)]
        public string DistributionText { get; set; }
    }

    [DataContract]
    internal sealed class BridgeRequest
    {
        [DataMember(Name = "protocol")]
        public int Protocol { get; set; }

        [DataMember(Name = "type")]
        public string Type { get; set; }

        [DataMember(Name = "request_id")]
        public string RequestId { get; set; }

        [DataMember(Name = "token", EmitDefaultValue = false)]
        public string Token { get; set; }

        [DataMember(Name = "client", EmitDefaultValue = false)]
        public ClientIdentity Client { get; set; }

        [DataMember(Name = "payload", EmitDefaultValue = false)]
        public MeasurementPayload Payload { get; set; }
    }

    [DataContract]
    internal sealed class BridgeErrorInfo
    {
        [DataMember(Name = "code")]
        public string Code { get; set; }

        [DataMember(Name = "message")]
        public string Message { get; set; }
    }

    [DataContract]
    internal sealed class BridgeResponse
    {
        [DataMember(Name = "protocol")]
        public int Protocol { get; set; }

        [DataMember(Name = "type")]
        public string Type { get; set; }

        [DataMember(Name = "request_id")]
        public string RequestId { get; set; }

        [DataMember(Name = "ok")]
        public bool Ok { get; set; }

        [DataMember(Name = "error")]
        public BridgeErrorInfo Error { get; set; }

        [DataMember(Name = "result")]
        public Dictionary<string, object> Result { get; set; }
    }

    internal sealed class MetradosBridgeClient : IDisposable
    {
        internal const int ProtocolVersion = 1;
        internal const string ClientVersion = "0.1.0";
        private const int ConnectTimeoutMilliseconds = 400;
        private const int ResponseTimeoutMilliseconds = 5000;
        private const int MonitorPeriodMilliseconds = 3000;
        private const int MaximumResponseCharacters = 1048576;
        private static readonly object logSync = new object();
        private static string lastLogEntry;
        private static DateTime lastLogTimeUtc = DateTime.MinValue;

        private readonly object sync = new object();
        private readonly string autoCadRelease;
        private Timer monitor;
        private NamedPipeClientStream pipe;
        private StreamReader reader;
        private StreamWriter writer;
        private string connectedSessionId;
        private bool disposed;
        private int monitorActive;

        internal MetradosBridgeClient(string release, bool startMonitor)
        {
            autoCadRelease = release;
            if (startMonitor)
            {
                monitor = new Timer(MonitorConnection, null, 250, MonitorPeriodMilliseconds);
            }
        }

        internal bool IsConnected
        {
            get
            {
                lock (sync)
                {
                    return pipe != null && pipe.IsConnected && !string.IsNullOrEmpty(connectedSessionId);
                }
            }
        }

        internal bool PingNow(out string message)
        {
            lock (sync)
            {
                try
                {
                    EnsureConnected();
                    BridgeResponse response = Exchange(new BridgeRequest
                    {
                        Protocol = ProtocolVersion,
                        Type = "ping",
                        RequestId = Guid.NewGuid().ToString()
                    });
                    if (!response.Ok || response.Type != "pong")
                    {
                        throw new IOException(ResponseMessage(response));
                    }
                    message = "Metrados conectado correctamente.";
                    return true;
                }
                catch (Exception error)
                {
                    ResetConnection();
                    message = FriendlyMessage(error);
                    Log("connection_failed", message);
                    return false;
                }
            }
        }

        internal bool SendArea(MeasurementPayload measurement, out string message)
        {
            lock (sync)
            {
                try
                {
                    EnsureConnected();
                    BridgeResponse response = Exchange(new BridgeRequest
                    {
                        Protocol = ProtocolVersion,
                        Type = "area_measurement",
                        RequestId = Guid.NewGuid().ToString(),
                        Payload = measurement
                    });
                    if (!response.Ok)
                    {
                        message = ResponseMessage(response);
                        return false;
                    }
                    if (response.Type != "area_measurement_ack")
                    {
                        throw new IOException("Metrados devolvió una respuesta inesperada.");
                    }
                    message = "Área agregada a la partida activa de Metrados.";
                    return true;
                }
                catch (Exception error)
                {
                    ResetConnection();
                    message = FriendlyMessage(error);
                    Log("area_transfer_failed", message);
                    return false;
                }
            }
        }

        internal bool SendLength(MeasurementPayload measurement, out string message)
        {
            lock (sync)
            {
                try
                {
                    EnsureConnected();
                    BridgeResponse response = Exchange(new BridgeRequest
                    {
                        Protocol = ProtocolVersion,
                        Type = "length_measurement",
                        RequestId = Guid.NewGuid().ToString(),
                        Payload = measurement
                    });
                    if (!response.Ok)
                    {
                        message = ResponseMessage(response);
                        return false;
                    }
                    if (response.Type != "length_measurement_ack")
                    {
                        throw new IOException("Metrados devolvió una respuesta inesperada.");
                    }
                    message = "Longitud agregada a la partida activa de Metrados.";
                    return true;
                }
                catch (Exception error)
                {
                    ResetConnection();
                    message = FriendlyMessage(error);
                    Log("length_transfer_failed", message);
                    return false;
                }
            }
        }

        internal bool SendSteel(MeasurementPayload measurement, out string message)
        {
            lock (sync)
            {
                try
                {
                    EnsureConnected();
                    BridgeResponse response = Exchange(new BridgeRequest
                    {
                        Protocol = ProtocolVersion,
                        Type = "steel_distribution",
                        RequestId = Guid.NewGuid().ToString(),
                        Payload = measurement
                    });
                    if (!response.Ok)
                    {
                        message = ResponseMessage(response);
                        return false;
                    }
                    if (response.Type != "steel_distribution_ack")
                    {
                        throw new IOException("Metrados devolvió una respuesta inesperada.");
                    }
                    message = "Detalle de acero agregado a la partida activa de Metrados.";
                    return true;
                }
                catch (Exception error)
                {
                    ResetConnection();
                    message = FriendlyMessage(error);
                    Log("steel_transfer_failed", message);
                    return false;
                }
            }
        }

        private void MonitorConnection(object state)
        {
            if (Interlocked.Exchange(ref monitorActive, 1) != 0)
            {
                return;
            }
            try
            {
                string ignored;
                PingNow(out ignored);
            }
            finally
            {
                Interlocked.Exchange(ref monitorActive, 0);
            }
        }

        private void EnsureConnected()
        {
            if (disposed)
            {
                throw new ObjectDisposedException("MetradosBridgeClient");
            }
            SessionDescriptor descriptor = ReadSession();
            if (descriptor.Protocol != ProtocolVersion)
            {
                throw new IOException("Metrados utiliza una versión de conexión incompatible.");
            }
            if (string.IsNullOrWhiteSpace(descriptor.Pipe) ||
                string.IsNullOrWhiteSpace(descriptor.Token) ||
                string.IsNullOrWhiteSpace(descriptor.SessionId))
            {
                throw new IOException("La sesión publicada por Metrados está incompleta.");
            }
            if (pipe != null && pipe.IsConnected && connectedSessionId == descriptor.SessionId)
            {
                return;
            }

            ResetConnection();
            NamedPipeClientStream candidate = new NamedPipeClientStream(
                ".", descriptor.Pipe, PipeDirection.InOut, PipeOptions.None);
            try
            {
                candidate.Connect(ConnectTimeoutMilliseconds);
                candidate.ReadMode = PipeTransmissionMode.Byte;
                pipe = candidate;
                reader = new StreamReader(pipe, new UTF8Encoding(false, true), false, 4096, true);
                writer = new StreamWriter(pipe, new UTF8Encoding(false, true), 4096, true);
                writer.NewLine = "\n";
                writer.AutoFlush = true;
                string requestId = Guid.NewGuid().ToString();
                BridgeResponse response = Exchange(new BridgeRequest
                {
                    Protocol = ProtocolVersion,
                    Type = "hello",
                    RequestId = requestId,
                    Token = descriptor.Token,
                    Client = new ClientIdentity
                    {
                        Name = "Metrados.AutoCAD2021",
                        Version = ClientVersion,
                        ProcessId = Process.GetCurrentProcess().Id,
                        AutoCadRelease = autoCadRelease
                    }
                });
                if (!response.Ok || response.Type != "hello_ack" || response.RequestId != requestId)
                {
                    throw new IOException(ResponseMessage(response));
                }
                connectedSessionId = descriptor.SessionId;
                Log("connected", "session=" + descriptor.SessionId);
            }
            catch
            {
                candidate.Dispose();
                ResetConnection();
                throw;
            }
        }

        private BridgeResponse Exchange(BridgeRequest request)
        {
            if (writer == null || reader == null)
            {
                throw new IOException("La conexión local no está abierta.");
            }
            writer.WriteLine(Serialize(request));
            Task<string> pending = Task.Factory.StartNew(
                () => ReadBoundedLine(reader), CancellationToken.None,
                TaskCreationOptions.DenyChildAttach, TaskScheduler.Default);
            string line;
            try
            {
                if (!pending.Wait(ResponseTimeoutMilliseconds))
                {
                    ResetConnection();
                    throw new TimeoutException("Metrados no respondió dentro del tiempo esperado.");
                }
                line = pending.Result;
            }
            catch (AggregateException error)
            {
                throw new IOException("Se interrumpió la respuesta de Metrados.", error.GetBaseException());
            }
            if (line == null)
            {
                throw new EndOfStreamException("Metrados cerró la conexión.");
            }
            BridgeResponse response = Deserialize<BridgeResponse>(line);
            if (response.Protocol != ProtocolVersion || response.RequestId != request.RequestId)
            {
                throw new IOException("Metrados devolvió una respuesta que no corresponde a la solicitud.");
            }
            return response;
        }

        private static string ReadBoundedLine(StreamReader input)
        {
            StringBuilder value = new StringBuilder();
            while (true)
            {
                int character = input.Read();
                if (character < 0)
                {
                    return value.Length == 0 ? null : value.ToString();
                }
                if (character == '\n')
                {
                    return value.ToString();
                }
                if (character != '\r')
                {
                    value.Append((char)character);
                    if (value.Length > MaximumResponseCharacters)
                    {
                        throw new IOException("La respuesta de Metrados excede el límite permitido.");
                    }
                }
            }
        }

        private static SessionDescriptor ReadSession()
        {
            string path = SessionPath();
            if (!File.Exists(path))
            {
                throw new FileNotFoundException("Abre Metrados antes de usar la conexión con AutoCAD.", path);
            }
            return Deserialize<SessionDescriptor>(File.ReadAllText(path, Encoding.UTF8));
        }

        private static string SessionPath()
        {
            string configured = Environment.GetEnvironmentVariable("METRADOS_BRIDGE_SESSION");
            if (!string.IsNullOrWhiteSpace(configured))
            {
                return configured;
            }
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                                "Metrados", "bridge", "session.json");
        }

        private static string Serialize<T>(T value)
        {
            DataContractJsonSerializer serializer = new DataContractJsonSerializer(typeof(T));
            using (MemoryStream output = new MemoryStream())
            {
                serializer.WriteObject(output, value);
                return Encoding.UTF8.GetString(output.ToArray());
            }
        }

        private static T Deserialize<T>(string value)
        {
            DataContractJsonSerializer serializer = new DataContractJsonSerializer(typeof(T));
            using (MemoryStream input = new MemoryStream(Encoding.UTF8.GetBytes(value)))
            {
                return (T)serializer.ReadObject(input);
            }
        }

        private static string ResponseMessage(BridgeResponse response)
        {
            if (response != null && response.Error != null && !string.IsNullOrWhiteSpace(response.Error.Message))
            {
                return response.Error.Message;
            }
            return "Metrados rechazó la solicitud de conexión.";
        }

        private static string FriendlyMessage(Exception error)
        {
            if (error is TimeoutException)
            {
                return "Metrados está abierto, pero la conexión local no respondió.";
            }
            if (error is FileNotFoundException)
            {
                return "Metrados no está abierto o todavía no publicó la conexión.";
            }
            return string.IsNullOrWhiteSpace(error.Message)
                ? "No se pudo conectar con Metrados."
                : error.Message;
        }

        private void ResetConnection()
        {
            connectedSessionId = null;
            if (writer != null)
            {
                writer.Dispose();
                writer = null;
            }
            if (reader != null)
            {
                reader.Dispose();
                reader = null;
            }
            if (pipe != null)
            {
                pipe.Dispose();
                pipe = null;
            }
        }

        private static void Log(string eventName, string detail)
        {
            try
            {
                lock (logSync)
                {
                    string entry = eventName + " " + detail;
                    DateTime now = DateTime.UtcNow;
                    if (entry == lastLogEntry && now - lastLogTimeUtc < TimeSpan.FromMinutes(1))
                    {
                        return;
                    }
                    string folder = Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                        "Metrados", "bridge");
                    Directory.CreateDirectory(folder);
                    string path = Path.Combine(folder, "autocad.log");
                    string backup = path + ".1";
                    if (File.Exists(path) && new FileInfo(path).Length > 1048576)
                    {
                        if (File.Exists(backup))
                        {
                            File.Delete(backup);
                        }
                        File.Move(path, backup);
                    }
                    string line = now.ToString("o") + " " + entry + Environment.NewLine;
                    File.AppendAllText(path, line, Encoding.UTF8);
                    lastLogEntry = entry;
                    lastLogTimeUtc = now;
                }
            }
            catch
            {
                // Diagnostics must never interfere with AutoCAD.
            }
        }

        public void Dispose()
        {
            lock (sync)
            {
                disposed = true;
                if (monitor != null)
                {
                    monitor.Dispose();
                    monitor = null;
                }
                ResetConnection();
            }
        }
    }
}
