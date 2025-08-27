using Microsoft.SqlServer.Server;
using System.Data.SqlTypes;
using System.IO.MemoryMappedFiles;
using System.IO; // Added this line

public class UserDefinedFunctions
{
    [SqlFunction]
        /// <summary>
        /// Executes a model query against a binary model file stored at the specified path.
        /// </summary>
        /// <param name="modelPath">The path to the model file on disk.</param>
        /// <param name="offset">The byte offset within the model file to begin reading.</param>
        /// <param name="length">The number of bytes to read from the model file.</param>
        /// <returns>A SqlBytes object containing the requested segment of the model file.</returns>
        /// <exception cref="System.IO.IOException">Thrown when the file cannot be accessed or read.</exception>
        /// <exception cref="System.ArgumentException">Thrown when the arguments are invalid.</exception>
        public static SqlBytes QueryModel(SqlString modelPath, SqlInt64 offset, SqlInt32 length)
        {
            if (modelPath.IsNull || offset.IsNull || length.IsNull)
            {
                return new SqlBytes(); // Return empty if any input is null
            }
            try
            {
                using (FileStream fs = new FileStream(modelPath.Value, FileMode.Open, FileAccess.Read))
                {
                    fs.Seek(offset.Value, SeekOrigin.Begin);
                    byte[] buffer = new byte[length.Value];
                    fs.Read(buffer, 0, length.Value);
                    return new SqlBytes(buffer);
                }
            }
            catch (System.IO.IOException ioEx)
            {
                System.Diagnostics.Trace.TraceError($"IO error querying model file: {ioEx.Message}");
                throw new System.Data.SqlTypes.SqlTypeException("IO error querying model file.", ioEx);
            }
            catch (System.ArgumentException argEx)
            {
                System.Diagnostics.Trace.TraceError($"Invalid argument for model query: {argEx.Message}");
                throw new System.Data.SqlTypes.SqlTypeException("Invalid argument for model query.", argEx);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Trace.TraceError($"Unknown error querying model file: {ex.Message}");
                throw new System.Data.SqlTypes.SqlTypeException("Unknown error querying model file.", ex);
            }
        }
    }
}