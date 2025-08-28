import asyncio
import json
import logging

from db_connectors import get_sql_server_connection
from llm_connector import LLMClient


def prune_tree(root, min_score=0):
    """Prune the tree by removing children below min_score."""
    if not hasattr(root, "children"):
        return root
    pruned_children = [c for c in root.children if c.score >= min_score]
    for child in pruned_children:
        prune_tree(child, min_score)
    root.children = pruned_children
    return root


def select_best_thought(root):
    """Select the best thought from the tree (highest score, depth-first)."""
    best = root
    stack = [root]
    while stack:
        node = stack.pop()
        if node.score > best.score:
            best = node
        stack.extend(node.children)
    return best


class Thought:
    def __init__(
        self,
        text: str,
        score: float = 0.0,
        parent: "Thought" = None,
        log_id: int = None,
    ):
        self.text = text
        self.score = score
        self.parent = parent
        self.children = []
        self.log_id = log_id

    def add_child(self, child: "Thought"):
        self.children.append(child)

    def to_dict(self):
        return {
            "text": self.text,
            "score": self.score,
            "children": [child.to_dict() for child in self.children],
        }


logger = logging.getLogger(__name__)


async def update_agent_log_thought_tree(
    sql_server_conn,
    log_id: int,
    thought_tree_json: str
):
    """Updates the ThoughtTree JSON column in AgentLogs table."""
    cursor = await asyncio.to_thread(sql_server_conn.cursor)
    await asyncio.to_thread(
        cursor.execute,
        "UPDATE AgentLogs SET ThoughtTree = ? WHERE LogID = ?",
        thought_tree_json,
        log_id,
    )

async def expand_thought_tree(thought: Thought, llm_client: LLMClient):
    """Expands a thought by generating and evaluating child thoughts."""
    # Generate child thoughts
    generation_prompt = f"Given the thought \"{thought.text}\", generate 3 possible next thoughts as a JSON list of strings."
    try:
        response_text = await llm_client.invoke(generation_prompt)
        child_thought_texts = json.loads(response_text)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Error decoding LLM response for thought generation: {e}")
        return

    # Evaluate child thoughts
    for child_text in child_thought_texts:
        evaluation_prompt = f"Evaluate the following thought on a scale of 0 to 1, where 1 is the best: \"{child_text}\". Respond with a JSON object with a single key, 'score'."
        try:
            response_text = await llm_client.invoke(evaluation_prompt)
            score_data = json.loads(response_text)
            score = float(score_data.get('score', 0.0))
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.error(f"Error decoding LLM response for thought evaluation: {e}")
            score = 0.0
        
        child_thought = Thought(child_text, score=score, parent=thought, log_id=thought.log_id)
        thought.add_child(child_thought)


async def initiate_tree_of_thought(initial_query, agent_id, llm_client: LLMClient):
    conn = await get_sql_server_connection()
    if not conn:
        return None
    try:
        cursor = await asyncio.to_thread(conn.cursor)
        await asyncio.to_thread(
            cursor.execute,
            "INSERT INTO AgentLogs (AgentID, Problem, ThoughtTree) VALUES (?, ?, ?);",
            agent_id,
            initial_query,
            json.dumps({"root": initial_query}),
        )
        log_id = await asyncio.to_thread(getattr, cursor, "lastrowid", None)
        root_thought = Thought(initial_query, log_id=log_id)
        
        await expand_thought_tree(root_thought, llm_client)

        if log_id is not None:
            await update_agent_log_thought_tree(
                conn, log_id, json.dumps(root_thought.to_dict())
            )
        
        await asyncio.to_thread(conn.commit)
        return root_thought
    except Exception as e:
        logger.error(f"Error in initiate_tree_of_thought: {e}", exc_info=True)
        if conn:
            await asyncio.to_thread(conn.rollback)
        return None
    finally:
        if conn:
            await asyncio.to_thread(conn.close)
