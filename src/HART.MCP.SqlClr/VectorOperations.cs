using System;
using System.Data;
using System.Data.SqlClient;
using System.Data.SqlTypes;
using Microsoft.SqlServer.Server;
using System.Collections.Generic;
using System.Text;
using System.IO;
using System.Linq;

namespace HART.MCP.SqlClr
{
    public partial class VectorOperations
    {
        [Microsoft.SqlServer.Server.SqlFunction(
            Name = "CalculateCosineSimilarity",
            IsDeterministic = true,
            IsPrecise = false,
            DataAccess = DataAccessKind.None)]
        public static SqlDouble CalculateCosineSimilarity(SqlString vector1Json, SqlString vector2Json)
        {
            if (vector1Json.IsNull || vector2Json.IsNull)
                return SqlDouble.Null;

            try
            {
                var vec1 = ParseVectorFromJson(vector1Json.Value);
                var vec2 = ParseVectorFromJson(vector2Json.Value);

                if (vec1.Length != vec2.Length)
                    throw new ArgumentException("Vectors must have the same dimensionality");

                double dotProduct = 0.0;
                double magnitude1 = 0.0;
                double magnitude2 = 0.0;

                for (int i = 0; i < vec1.Length; i++)
                {
                    dotProduct += vec1[i] * vec2[i];
                    magnitude1 += vec1[i] * vec1[i];
                    magnitude2 += vec2[i] * vec2[i];
                }

                magnitude1 = Math.Sqrt(magnitude1);
                magnitude2 = Math.Sqrt(magnitude2);

                if (magnitude1 == 0.0 || magnitude2 == 0.0)
                    return 0.0;

                return dotProduct / (magnitude1 * magnitude2);
            }
            catch (Exception ex)
            {
                throw new SystemException($"Error calculating cosine similarity: {ex.Message}");
            }
        }

        [Microsoft.SqlServer.Server.SqlFunction(
            Name = "CalculateEuclideanDistance",
            IsDeterministic = true,
            IsPrecise = false,
            DataAccess = DataAccessKind.None)]
        public static SqlDouble CalculateEuclideanDistance(SqlString vector1Json, SqlString vector2Json)
        {
            if (vector1Json.IsNull || vector2Json.IsNull)
                return SqlDouble.Null;

            try
            {
                var vec1 = ParseVectorFromJson(vector1Json.Value);
                var vec2 = ParseVectorFromJson(vector2Json.Value);

                if (vec1.Length != vec2.Length)
                    throw new ArgumentException("Vectors must have the same dimensionality");

                double sumSquaredDiffs = 0.0;
                for (int i = 0; i < vec1.Length; i++)
                {
                    double diff = vec1[i] - vec2[i];
                    sumSquaredDiffs += diff * diff;
                }

                return Math.Sqrt(sumSquaredDiffs);
            }
            catch (Exception ex)
            {
                throw new SystemException($"Error calculating Euclidean distance: {ex.Message}");
            }
        }

        [Microsoft.SqlServer.Server.SqlFunction(
            Name = "FindTopKSimilar",
            FillRowMethodName = "FillSimilarityRow",
            TableDefinition = "DocumentId UNIQUEIDENTIFIER, Similarity FLOAT")]
        public static IEnumerable<SimilarityResult> FindTopKSimilar(SqlString queryVectorJson, SqlString embeddingTableName, SqlInt32 topK)
        {
            if (queryVectorJson.IsNull || embeddingTableName.IsNull)
                yield break;

            var queryVector = ParseVectorFromJson(queryVectorJson.Value);
            var results = new List<SimilarityResult>();

            // This would normally query the embedding table, but for CLR safety,
            // we'll return a simplified implementation
            using (var connection = new SqlConnection("context connection=true"))
            {
                connection.Open();
                var sql = $@"
                    SELECT TOP ({topK.Value}) 
                        DocumentId, 
                        EmbeddingVector 
                    FROM {embeddingTableName.Value}
                    WHERE EmbeddingVector IS NOT NULL";

                using (var command = new SqlCommand(sql, connection))
                {
                    using (var reader = command.ExecuteReader())
                    {
                        while (reader.Read())
                        {
                            try
                            {
                                var docId = reader.GetGuid(reader.GetOrdinal("DocumentId"));
                                var vectorJson = reader.GetString(reader.GetOrdinal("EmbeddingVector"));
                                var docVector = ParseVectorFromJson(vectorJson);
                                
                                var similarity = CosineSimilarity(queryVector, docVector);
                                results.Add(new SimilarityResult { DocumentId = docId, Similarity = similarity });
                            }
                            catch
                            {
                                // Skip invalid vectors
                                continue;
                            }
                        }
                    }
                }
            }

            // Sort by similarity descending and return top K
            results.Sort((a, b) => b.Similarity.CompareTo(a.Similarity));
            foreach (var result in results.Take(topK.Value))
            {
                yield return result;
            }
        }

        public static void FillSimilarityRow(object obj, out SqlGuid documentId, out SqlDouble similarity)
        {
            var result = (SimilarityResult)obj;
            documentId = result.DocumentId;
            similarity = result.Similarity;
        }

        [Microsoft.SqlServer.Server.SqlFunction(
            Name = "NormalizeVector",
            IsDeterministic = true,
            IsPrecise = false,
            DataAccess = DataAccessKind.None)]
        public static SqlString NormalizeVector(SqlString vectorJson)
        {
            if (vectorJson.IsNull)
                return SqlString.Null;

            try
            {
                var vector = ParseVectorFromJson(vectorJson.Value);
                var magnitude = Math.Sqrt(vector.Sum(x => x * x));

                if (magnitude == 0.0)
                    return vectorJson;

                var normalizedVector = vector.Select(x => x / magnitude).ToArray();
                return SerializeVectorToJson(normalizedVector);
            }
            catch (Exception ex)
            {
                throw new SystemException($"Error normalizing vector: {ex.Message}");
            }
        }

        [Microsoft.SqlServer.Server.SqlFunction(
            Name = "VectorDimension",
            IsDeterministic = true,
            IsPrecise = true,
            DataAccess = DataAccessKind.None)]
        public static SqlInt32 VectorDimension(SqlString vectorJson)
        {
            if (vectorJson.IsNull)
                return SqlInt32.Null;

            try
            {
                var vector = ParseVectorFromJson(vectorJson.Value);
                return vector.Length;
            }
            catch
            {
                return SqlInt32.Null;
            }
        }

        // Helper methods
        private static double[] ParseVectorFromJson(string vectorJson)
        {
            // Simple JSON array parsing for vectors like [1.0, 2.0, 3.0]
            if (string.IsNullOrWhiteSpace(vectorJson))
                throw new ArgumentException("Vector JSON cannot be empty");

            vectorJson = vectorJson.Trim();
            if (!vectorJson.StartsWith("[") || !vectorJson.EndsWith("]"))
                throw new ArgumentException("Vector JSON must be an array");

            var content = vectorJson.Substring(1, vectorJson.Length - 2);
            if (string.IsNullOrWhiteSpace(content))
                return new double[0];

            var elements = content.Split(',');
            var result = new double[elements.Length];

            for (int i = 0; i < elements.Length; i++)
            {
                if (!double.TryParse(elements[i].Trim(), out result[i]))
                    throw new ArgumentException($"Invalid number format at index {i}: {elements[i]}");
            }

            return result;
        }

        private static string SerializeVectorToJson(double[] vector)
        {
            var sb = new StringBuilder();
            sb.Append('[');
            for (int i = 0; i < vector.Length; i++)
            {
                if (i > 0) sb.Append(',');
                sb.Append(vector[i].ToString("G17"));
            }
            sb.Append(']');
            return sb.ToString();
        }

        private static double CosineSimilarity(double[] vec1, double[] vec2)
        {
            if (vec1.Length != vec2.Length)
                return 0.0;

            double dotProduct = 0.0;
            double magnitude1 = 0.0;
            double magnitude2 = 0.0;

            for (int i = 0; i < vec1.Length; i++)
            {
                dotProduct += vec1[i] * vec2[i];
                magnitude1 += vec1[i] * vec1[i];
                magnitude2 += vec2[i] * vec2[i];
            }

            magnitude1 = Math.Sqrt(magnitude1);
            magnitude2 = Math.Sqrt(magnitude2);

            if (magnitude1 == 0.0 || magnitude2 == 0.0)
                return 0.0;

            return dotProduct / (magnitude1 * magnitude2);
        }

        public struct SimilarityResult
        {
            public Guid DocumentId;
            public double Similarity;
        }
    }
}