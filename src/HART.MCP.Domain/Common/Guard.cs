namespace HART.MCP.Domain.Common;

public static class Guard
{
    public static class Against
    {
        public static string NullOrWhiteSpace(string? input, string parameterName)
        {
            if (string.IsNullOrWhiteSpace(input))
                throw new ArgumentException($"Required input {parameterName} was null or whitespace.", parameterName);
            return input;
        }

        public static T Null<T>(T? input, string parameterName) where T : class
        {
            if (input == null)
                throw new ArgumentNullException(parameterName);
            return input;
        }

        public static T Default<T>(T input, string parameterName) where T : struct
        {
            if (EqualityComparer<T>.Default.Equals(input, default(T)))
                throw new ArgumentException($"Required input {parameterName} was default value.", parameterName);
            return input;
        }

        public static int Negative(int input, string parameterName)
        {
            if (input < 0)
                throw new ArgumentException($"Required input {parameterName} cannot be negative.", parameterName);
            return input;
        }

        public static long Negative(long input, string parameterName)
        {
            if (input < 0)
                throw new ArgumentException($"Required input {parameterName} cannot be negative.", parameterName);
            return input;
        }

        public static int NegativeOrZero(int input, string parameterName)
        {
            if (input <= 0)
                throw new ArgumentException($"Required input {parameterName} cannot be negative or zero.", parameterName);
            return input;
        }

        public static T[] NullOrEmpty<T>(T[]? input, string parameterName)
        {
            if (input == null || input.Length == 0)
                throw new ArgumentException($"Required input {parameterName} cannot be null or empty.", parameterName);
            return input;
        }
    }
}