using System;
using System.Data;
using System.Data.SqlClient;
using System.Data.SqlTypes;
using Microsoft.SqlServer.Server;
using System.Collections.Generic;
using System.Text;
using System.IO;
using System.Security.Cryptography;

namespace HART.MCP.SqlClr
{
    public partial class FileStreamOperations
    {
        [Microsoft.SqlServer.Server.SqlFunction(
            Name = "ExtractTextFromFile",
            IsDeterministic = false,
            IsPrecise = false,
            DataAccess = DataAccessKind.Read)]
        public static SqlString ExtractTextFromFile(SqlString filePath)
        {
            if (filePath.IsNull)
                return SqlString.Null;

            try
            {
                string path = filePath.Value;
                if (!File.Exists(path))
                    return SqlString.Null;

                var fileInfo = new FileInfo(path);
                var extension = fileInfo.Extension.ToLowerInvariant();

                switch (extension)
                {
                    case ".txt":
                    case ".md":
                    case ".csv":
                        return File.ReadAllText(path, Encoding.UTF8);
                    
                    case ".json":
                        return ExtractJsonContent(path);
                    
                    case ".xml":
                        return ExtractXmlContent(path);
                    
                    default:
                        // For binary files, return base64 encoding
                        var bytes = File.ReadAllBytes(path);
                        if (bytes.Length > 50 * 1024 * 1024) // 50MB limit
                            return "File too large for processing";
                        
                        return Convert.ToBase64String(bytes);
                }
            }
            catch (Exception ex)
            {
                return $"Error reading file: {ex.Message}";
            }
        }

        [Microsoft.SqlServer.Server.SqlFunction(
            Name = "CalculateFileHash",
            IsDeterministic = false,
            IsPrecise = true,
            DataAccess = DataAccessKind.None)]
        public static SqlString CalculateFileHash(SqlString filePath, SqlString hashAlgorithm)
        {
            if (filePath.IsNull)
                return SqlString.Null;

            try
            {
                string path = filePath.Value;
                if (!File.Exists(path))
                    return SqlString.Null;

                string algorithm = hashAlgorithm.IsNull ? "SHA256" : hashAlgorithm.Value.ToUpperInvariant();
                
                using (var stream = File.OpenRead(path))
                {
                    HashAlgorithm hasher;
                    switch (algorithm)
                    {
                        case "MD5":
                            hasher = MD5.Create();
                            break;
                        case "SHA1":
                            hasher = SHA1.Create();
                            break;
                        case "SHA256":
                        default:
                            hasher = SHA256.Create();
                            break;
                    }

                    using (hasher)
                    {
                        var hashBytes = hasher.ComputeHash(stream);
                        return BitConverter.ToString(hashBytes).Replace("-", "").ToLowerInvariant();
                    }
                }
            }
            catch (Exception ex)
            {
                return $"Error calculating hash: {ex.Message}";
            }
        }

        [Microsoft.SqlServer.Server.SqlFunction(
            Name = "GetFileMetadata",
            IsDeterministic = false,
            IsPrecise = false,
            DataAccess = DataAccessKind.None)]
        public static SqlString GetFileMetadata(SqlString filePath)
        {
            if (filePath.IsNull)
                return SqlString.Null;

            try
            {
                string path = filePath.Value;
                if (!File.Exists(path))
                    return SqlString.Null;

                var fileInfo = new FileInfo(path);
                var metadata = new StringBuilder();
                
                metadata.Append("{");
                metadata.Append($"\"name\":\"{EscapeJsonString(fileInfo.Name)}\",");
                metadata.Append($"\"size\":{fileInfo.Length},");
                metadata.Append($"\"extension\":\"{EscapeJsonString(fileInfo.Extension)}\",");
                metadata.Append($"\"createdAt\":\"{fileInfo.CreationTimeUtc:yyyy-MM-ddTHH:mm:ss.fffZ}\",");
                metadata.Append($"\"modifiedAt\":\"{fileInfo.LastWriteTimeUtc:yyyy-MM-ddTHH:mm:ss.fffZ}\",");
                metadata.Append($"\"isReadOnly\":{fileInfo.IsReadOnly.ToString().ToLowerInvariant()}");
                metadata.Append("}");

                return metadata.ToString();
            }
            catch (Exception ex)
            {
                return $"{{\"error\":\"Error getting metadata: {EscapeJsonString(ex.Message)}\"}}";
            }
        }

        [Microsoft.SqlServer.Server.SqlFunction(
            Name = "ChunkTextFile",
            FillRowMethodName = "FillTextChunkRow",
            TableDefinition = "ChunkIndex INT, ChunkText NVARCHAR(MAX), ChunkSize INT")]
        public static IEnumerable<TextChunk> ChunkTextFile(SqlString filePath, SqlInt32 chunkSize, SqlInt32 overlapSize)
        {
            if (filePath.IsNull)
                yield break;
                
            var chunks = new List<TextChunk>();

            try
            {
                string path = filePath.Value;
                if (!File.Exists(path))
                    yield break;

                string content = File.ReadAllText(path, Encoding.UTF8);
                int chunkSizeValue = chunkSize.IsNull ? 1000 : chunkSize.Value;
                int overlapSizeValue = overlapSize.IsNull ? 100 : overlapSize.Value;

                int currentIndex = 0;
                int chunkIndex = 0;

                while (currentIndex < content.Length)
                {
                    int endIndex = Math.Min(currentIndex + chunkSizeValue, content.Length);
                    string chunkText = content.Substring(currentIndex, endIndex - currentIndex);
                    
                    chunks.Add(new TextChunk
                    {
                        ChunkIndex = chunkIndex,
                        ChunkText = chunkText,
                        ChunkSize = chunkText.Length
                    });

                    currentIndex += chunkSizeValue - overlapSizeValue;
                    chunkIndex++;

                    if (currentIndex >= content.Length)
                        break;
                }
            }
            catch
            {
                yield break;
            }

            foreach (var chunk in chunks)
            {
                yield return chunk;
            }
        }

        public static void FillTextChunkRow(object obj, out SqlInt32 chunkIndex, out SqlString chunkText, out SqlInt32 chunkSize)
        {
            var chunk = (TextChunk)obj;
            chunkIndex = chunk.ChunkIndex;
            chunkText = chunk.ChunkText;
            chunkSize = chunk.ChunkSize;
        }

        [Microsoft.SqlServer.Server.SqlFunction(
            Name = "CompressText",
            IsDeterministic = true,
            IsPrecise = false,
            DataAccess = DataAccessKind.None)]
        public static SqlBytes CompressText(SqlString inputText)
        {
            if (inputText.IsNull || string.IsNullOrEmpty(inputText.Value))
                return SqlBytes.Null;

            try
            {
                byte[] inputBytes = Encoding.UTF8.GetBytes(inputText.Value);
                using (var memoryStream = new MemoryStream())
                {
                    using (var gzipStream = new System.IO.Compression.GZipStream(memoryStream, System.IO.Compression.CompressionMode.Compress))
                    {
                        gzipStream.Write(inputBytes, 0, inputBytes.Length);
                    }
                    return new SqlBytes(memoryStream.ToArray());
                }
            }
            catch (Exception ex)
            {
                throw new SystemException($"Error compressing text: {ex.Message}");
            }
        }

        [Microsoft.SqlServer.Server.SqlFunction(
            Name = "DecompressText",
            IsDeterministic = true,
            IsPrecise = false,
            DataAccess = DataAccessKind.None)]
        public static SqlString DecompressText(SqlBytes compressedData)
        {
            if (compressedData.IsNull)
                return SqlString.Null;

            try
            {
                using (var memoryStream = new MemoryStream(compressedData.Value))
                {
                    using (var gzipStream = new System.IO.Compression.GZipStream(memoryStream, System.IO.Compression.CompressionMode.Decompress))
                    {
                        using (var reader = new StreamReader(gzipStream, Encoding.UTF8))
                        {
                            return reader.ReadToEnd();
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                throw new SystemException($"Error decompressing text: {ex.Message}");
            }
        }

        // Helper methods
        private static string ExtractJsonContent(string filePath)
        {
            try
            {
                string jsonContent = File.ReadAllText(filePath, Encoding.UTF8);
                // Basic JSON validation and pretty-printing
                return jsonContent.Trim();
            }
            catch
            {
                return "Invalid JSON file";
            }
        }

        private static string ExtractXmlContent(string filePath)
        {
            try
            {
                string xmlContent = File.ReadAllText(filePath, Encoding.UTF8);
                // Basic XML validation
                return xmlContent.Trim();
            }
            catch
            {
                return "Invalid XML file";
            }
        }

        private static string EscapeJsonString(string input)
        {
            if (string.IsNullOrEmpty(input))
                return input;

            return input.Replace("\\", "\\\\")
                       .Replace("\"", "\\\"")
                       .Replace("\n", "\\n")
                       .Replace("\r", "\\r")
                       .Replace("\t", "\\t");
        }

        public struct TextChunk
        {
            public int ChunkIndex;
            public string ChunkText;
            public int ChunkSize;
        }
    }
}