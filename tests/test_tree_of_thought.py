import json
from unittest.mock import MagicMock, patch

import pytest

from tree_of_thought import (
    Thought,
    expand_thought_tree,
    initiate_tree_of_thought,
    prune_tree,
    select_best_thought,
    update_agent_log_thought_tree,
)


# Mock db_connectors.get_sql_server_connection
@pytest.fixture
def mock_sql_server_connection():
    with patch("tree_of_thought.get_sql_server_connection") as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        del mock_conn.__await__  # Remove the __await__ method from the MagicMock
        yield mock_conn, mock_cursor


# Mock rag_pipeline.generate_response
@pytest.fixture
def mock_generate_response():
    with patch("tree_of_thought.generate_response") as mock_gen_resp:
        mock_gen_resp.return_value = {
            "responses": {
                "milvus": [
                    {"id": "chunk1", "distance": 0.1, "text": "context 1"},
                    {"id": "chunk2", "distance": 0.2, "text": "context 2"},
                ]
            },
            "final_response": "mocked response",
        }
        yield mock_gen_resp


# --- Tests for Thought class ---
def test_thought_initialization():
    thought = Thought("initial thought", score=10, log_id=1)
    assert thought.text == "initial thought"
    assert thought.score == 10
    assert thought.log_id == 1
    assert thought.children == []


def test_thought_to_dict():
    thought = Thought("parent")
    child1 = Thought("child1")
    child2 = Thought("child2")
    thought.children.append(child1)
    thought.children.append(child2)
    expected_dict = {
        "text": "parent",
        "score": 0,
        "children": [
            {"text": "child1", "score": 0, "children": []},
            {"text": "child2", "score": 0, "children": []},
        ],
    }
    assert thought.to_dict() == expected_dict


# --- Tests for update_agent_log_thought_tree ---
def test_update_agent_log_thought_tree(mock_sql_server_connection):
    mock_conn, mock_cursor = mock_sql_server_connection
    log_id = 123
    thought_tree_json = json.dumps({"text": "test"})
    update_agent_log_thought_tree(mock_conn, log_id, thought_tree_json)
    mock_cursor.execute.assert_called_once_with(
        "UPDATE AgentLogs SET ThoughtTree = ? WHERE LogID = ?",
        thought_tree_json,
        log_id,
    )
    mock_conn.commit.assert_called_once()


# --- Tests for expand_thought ---
def test_expand_thought(mock_sql_server_connection, mock_generate_response):
    mock_conn, mock_cursor = mock_sql_server_connection
    root_thought = Thought("root problem", log_id=1)
    agent_id = 1
    log_id = 1

    expand_thought_tree(mock_conn, root_thought, agent_id, log_id, max_depth=1)

    assert len(root_thought.children) == 2  # Based on the 2 subthoughts generated
    assert (
        mock_generate_response.call_count == 1
    )  # generate_response is called once per thought expansion
    assert mock_cursor.execute.call_count == 2  # Called for each child thought update
    assert mock_conn.commit.call_count == 2


# --- Tests for prune_tree ---
def test_prune_tree():
    root = Thought("root")
    child1 = Thought("child1", score=5)
    child2 = Thought("child2", score=0)
    child3 = Thought("child3", score=3)
    root.children.extend([child1, child2, child3])

    prune_tree(root, min_score=2)
    assert len(root.children) == 2
    assert root.children[0].text == "child1"
    assert root.children[1].text == "child3"


# --- Tests for select_best_thought ---
def test_select_best_thought():
    root = Thought("root")
    child1 = Thought("child1", score=1)
    child2 = Thought("child2", score=10)
    child3 = Thought("child3", score=5)
    root.children.extend([child1, child2, child3])

    best = select_best_thought(root)
    assert best.text == "child2"

    # Test with no children
    single_thought = Thought("single")
    assert select_best_thought(single_thought) == single_thought


# --- Tests for initiate_tree_of_thought ---
def test_initiate_tree_of_thought(mock_sql_server_connection, mock_generate_response):
    mock_conn, mock_cursor = mock_sql_server_connection
    mock_cursor.lastrowid = 1  # Simulate a new log_id from lastrowid

    initial_query = "test problem"
    agent_id = 1

    root_thought = initiate_tree_of_thought(initial_query, agent_id)

    assert root_thought is not None
    assert root_thought.text == initial_query
    assert root_thought.log_id == 1

    # Verify initial AgentLog insert
    mock_cursor.execute.assert_any_call(
        "INSERT INTO AgentLogs (AgentID, Problem, ThoughtTree) VALUES (?, ?, ?);",
        agent_id,
        initial_query,
        json.dumps({"root": initial_query}),
    )
    assert mock_conn.commit.call_count >= 1
    # Connection close is not enforced in code, so do not assert


def test_initiate_tree_of_thought_connection_failure():
    with patch("tree_of_thought.get_sql_server_connection", return_value=None):
        root_thought = initiate_tree_of_thought("test problem", 1)
        assert root_thought is None
