using Microsoft.SqlServer.Server;
using System.Data.SqlTypes;
using System.IO.MemoryMappedFiles;
using System.IO; // Added this line

public class UserDefinedFunctions
{
    [SqlFunction]
    public static SqlBytes QueryModel(SqlString modelPath, SqlInt64 offset, SqlInt32 length)
    {
        if (modelPath.IsNull || offset.IsNull || length.IsNull)
        {
            return new SqlBytes(); // Return empty if any input is null
        }

        try
        {
            using (MemoryMappedFile mmf = MemoryMappedFile.CreateFromFile(
                modelPath.Value,
                FileMode.Open,
                null, // mapName
                0,    // capacity (0 means entire file)
                MemoryMappedFileAccess.Read))
            {
                using (MemoryMappedViewAccessor accessor = mmf.CreateViewAccessor(offset.Value, length.Value))
                {
                    byte[] buffer = new byte[length.Value];
                    accessor.ReadArray(0, buffer, 0, buffer.Length);
                    return new SqlBytes(buffer);
                }
            }
        }
        catch (System.Exception) // Removed 'ex'
        {
            // Log the exception or handle it as appropriate for SQL CLR
            // For simplicity, returning empty bytes on error
            return new SqlBytes();
        }
    }
}