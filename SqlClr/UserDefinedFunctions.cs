using Microsoft.SqlServer.Server;
using System.Data.SqlTypes;

public class UserDefinedFunctions
{
    [SqlFunction]
    public static SqlString HelloWorld()
    {
        return new SqlString("Hello, World from SQL CLR!");
    }
}