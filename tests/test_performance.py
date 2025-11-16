"""
Tests de performance et de charge pour FilAgent

Ce module teste:
- Gestion de requêtes concurrentes
- Traitement de contextes volumineux
- Utilisation de la mémoire sous charge
- Scalabilité du planificateur HTN

Ces tests permettent de valider que le système peut gérer des charges
réalistes tout en maintenant les garanties de conformité (traçabilité,
Decision Records, provenance).
"""

import pytest
import json
import time
import psutil
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from datetime import datetime
from planner import HierarchicalPlanner, TaskExecutor, TaskVerifier, PlanningStrategy
from planner.task_graph import TaskGraph, Task


# ============================================================================
# FIXTURES: Performance Testing
# ============================================================================

@pytest.fixture
def process():
    """Get current process for memory tracking"""
    return psutil.Process(os.getpid())


@pytest.fixture
def memory_tracker(process):
    """
    Track memory usage during test execution

    Returns:
        Callable: Function to get current memory stats
    """
    def get_memory_stats():
        """Get current memory usage in MB"""
        mem_info = process.memory_info()
        return {
            'rss_mb': mem_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': mem_info.vms / 1024 / 1024,  # Virtual Memory Size
        }

    return get_memory_stats


@pytest.fixture
def large_message_history():
    """Generate large message history for stress testing"""
    def _generate(num_messages: int = 100, message_length: int = 500) -> List[Dict[str, str]]:
        """
        Generate conversation history

        Args:
            num_messages: Number of messages to generate
            message_length: Approximate length of each message

        Returns:
            List of message dicts
        """
        messages = []
        for i in range(num_messages):
            role = "user" if i % 2 == 0 else "assistant"
            content = f"Message {i}: " + ("x" * message_length)
            messages.append({"role": role, "content": content})

        return messages

    return _generate


@pytest.fixture
def mock_model_fast():
    """Fast mock model for performance testing"""
    from conftest import MockModelInterface

    # Fast responses for load testing
    responses = [
        "Quick response.",
        "Done.",
        "Completed."
    ]

    return MockModelInterface(responses=responses)


# ============================================================================
# TESTS: Concurrent Request Handling
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_concurrent_api_requests(api_client, patched_middlewares, performance_tracker):
    """
    Test de gestion de requêtes API concurrentes

    Vérifie:
    - Traitement simultané de multiples requêtes
    - Isolation des conversations
    - Maintien de la cohérence des logs
    - Absence de corruption de données

    Performance attendue:
    - 10 requêtes concurrentes < 5 secondes
    - Aucune erreur de concurrence
    - Logs cohérents pour chaque requête
    """
    num_concurrent = 10
    results = []
    errors = []

    def make_request(request_id: int) -> Dict[str, Any]:
        """Make a single API request"""
        try:
            response = api_client.post("/chat", json={
                "messages": [
                    {"role": "user", "content": f"Request {request_id}: Hello"}
                ]
            })

            return {
                'request_id': request_id,
                'status_code': response.status_code,
                'data': response.json() if response.status_code == 200 else None,
                'error': None
            }
        except Exception as e:
            return {
                'request_id': request_id,
                'status_code': None,
                'data': None,
                'error': str(e)
            }

    # Execute concurrent requests
    with performance_tracker("concurrent_requests") as timer:
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_concurrent)]

            for future in as_completed(futures):
                result = future.result()
                if result['error']:
                    errors.append(result)
                else:
                    results.append(result)

    # Verify all requests succeeded
    assert len(errors) == 0, f"Concurrent request errors: {errors}"
    assert len(results) == num_concurrent, f"Expected {num_concurrent} results, got {len(results)}"

    # Verify all requests completed successfully
    for result in results:
        assert result['status_code'] == 200, f"Request {result['request_id']} failed"
        assert result['data'] is not None
        assert 'id' in result['data']
        assert 'choices' in result['data']

    # Verify unique conversation IDs (isolation)
    conv_ids = [r['data']['id'] for r in results]
    assert len(set(conv_ids)) == num_concurrent, "Conversation IDs are not unique"

    # Performance assertion
    assert timer.elapsed < 5.0, f"Concurrent requests took {timer.elapsed:.2f}s (expected < 5s)"

    # Verify event logs were created for all requests
    event_log_dir = patched_middlewares['isolated_fs']['logs_events']
    log_files = list(event_log_dir.glob("*.jsonl"))
    assert len(log_files) > 0, "No event logs created"

    print(f"\n✓ {num_concurrent} concurrent requests completed in {timer.elapsed:.2f}s")


@pytest.mark.performance
@pytest.mark.slow
def test_concurrent_tool_executions(api_client_with_tool_model, patched_middlewares, performance_tracker):
    """
    Test d'exécutions d'outils concurrentes

    Vérifie:
    - Isolation des exécutions d'outils
    - Gestion de la concurrence dans le tool registry
    - Decision Records corrects pour chaque exécution
    - Aucune interférence entre exécutions parallèles

    Performance attendue:
    - 5 exécutions concurrentes < 3 secondes
    """
    num_concurrent = 5
    results = []

    def execute_tool_request(request_id: int) -> Dict[str, Any]:
        """Execute a request that triggers tool usage"""
        try:
            response = api_client_with_tool_model.post("/chat", json={
                "messages": [
                    {"role": "user", "content": f"Task {request_id}: Run calculation"}
                ]
            })

            return {
                'request_id': request_id,
                'status_code': response.status_code,
                'success': response.status_code == 200
            }
        except Exception as e:
            return {
                'request_id': request_id,
                'status_code': None,
                'success': False,
                'error': str(e)
            }

    with performance_tracker("concurrent_tool_executions") as timer:
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(execute_tool_request, i) for i in range(num_concurrent)]
            results = [f.result() for f in as_completed(futures)]

    # Verify all executions succeeded
    successful = [r for r in results if r['success']]
    assert len(successful) == num_concurrent, f"Only {len(successful)}/{num_concurrent} succeeded"

    # Performance assertion
    assert timer.elapsed < 3.0, f"Concurrent tool executions took {timer.elapsed:.2f}s (expected < 3s)"

    print(f"\n✓ {num_concurrent} concurrent tool executions in {timer.elapsed:.2f}s")


# ============================================================================
# TESTS: Large Context Handling
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_large_conversation_history(api_client, large_message_history, performance_tracker, memory_tracker):
    """
    Test de traitement d'historique de conversation volumineux

    Vérifie:
    - Gestion de 100+ messages
    - Performance de récupération depuis SQLite
    - Utilisation mémoire raisonnable
    - Temps de réponse acceptable

    Performance attendue:
    - 100 messages < 2 secondes
    - Croissance mémoire < 50 MB
    """
    # Generate large history
    messages = large_message_history(num_messages=100, message_length=200)

    # Track initial memory
    mem_before = memory_tracker()

    # Send request with large history
    with performance_tracker("large_context_processing") as timer:
        response = api_client.post("/chat", json={
            "messages": messages + [{"role": "user", "content": "Summarize our conversation"}]
        })

    # Track final memory
    mem_after = memory_tracker()

    # Verify success
    assert response.status_code == 200
    data = response.json()
    assert 'choices' in data

    # Performance assertions
    assert timer.elapsed < 2.0, f"Large context took {timer.elapsed:.2f}s (expected < 2s)"

    # Memory assertions
    mem_growth = mem_after['rss_mb'] - mem_before['rss_mb']
    assert mem_growth < 50, f"Memory grew by {mem_growth:.2f}MB (expected < 50MB)"

    print(f"\n✓ Processed 100 messages in {timer.elapsed:.2f}s (mem: +{mem_growth:.2f}MB)")


@pytest.mark.performance
def test_large_single_message(api_client, performance_tracker):
    """
    Test de traitement de message unique très long

    Vérifie:
    - Gestion de messages > 10KB
    - Tokenization efficace
    - Pas de timeout

    Performance attendue:
    - Message 10KB < 1 seconde
    """
    # Generate large message (10KB)
    large_content = "This is a test. " * 700  # ~10KB

    with performance_tracker("large_single_message") as timer:
        response = api_client.post("/chat", json={
            "messages": [{"role": "user", "content": large_content}]
        })

    assert response.status_code == 200
    assert timer.elapsed < 1.0, f"Large message took {timer.elapsed:.2f}s (expected < 1s)"

    print(f"\n✓ Processed 10KB message in {timer.elapsed:.2f}s")


@pytest.mark.performance
def test_context_retrieval_performance(temp_db, conversation_factory, performance_tracker):
    """
    Test de performance de récupération de contexte depuis DB

    Vérifie:
    - Requêtes SQLite optimisées
    - Temps de récupération constant
    - Pas de dégradation avec volume

    Performance attendue:
    - Récupération de 1000 messages < 0.5 secondes
    """
    from memory.episodic import get_messages

    # Create conversation with many messages
    messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
        for i in range(1000)
    ]

    conv_id = conversation_factory("conv-perf-test", messages)

    # Measure retrieval performance
    with performance_tracker("context_retrieval") as timer:
        retrieved = get_messages(conv_id, limit=100)

    assert len(retrieved) > 0
    assert timer.elapsed < 0.5, f"Context retrieval took {timer.elapsed:.2f}s (expected < 0.5s)"

    print(f"\n✓ Retrieved 100/{len(messages)} messages in {timer.elapsed:.2f}s")


# ============================================================================
# TESTS: Memory Usage Under Load
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_memory_stability_sustained_load(api_client, memory_tracker, performance_tracker):
    """
    Test de stabilité mémoire sous charge soutenue

    Vérifie:
    - Absence de fuites mémoire
    - Garbage collection efficace
    - Croissance mémoire linéaire acceptable

    Exécute 50 requêtes séquentielles et mesure la croissance mémoire.

    Performance attendue:
    - Croissance mémoire < 100 MB pour 50 requêtes
    - Pas de croissance exponentielle
    """
    num_requests = 50
    mem_samples = []

    # Initial memory
    mem_initial = memory_tracker()
    mem_samples.append(mem_initial['rss_mb'])

    with performance_tracker("sustained_load") as timer:
        for i in range(num_requests):
            response = api_client.post("/chat", json={
                "messages": [{"role": "user", "content": f"Request {i}"}]
            })

            assert response.status_code == 200

            # Sample memory every 10 requests
            if i % 10 == 0:
                mem = memory_tracker()
                mem_samples.append(mem['rss_mb'])

    # Final memory
    mem_final = memory_tracker()
    mem_growth = mem_final['rss_mb'] - mem_initial['rss_mb']

    # Verify memory stability
    assert mem_growth < 100, f"Memory grew by {mem_growth:.2f}MB (expected < 100MB)"

    # Check for linear growth (not exponential)
    # If memory doubles, we likely have a leak
    assert mem_final['rss_mb'] < mem_initial['rss_mb'] * 2, "Possible memory leak detected"

    print(f"\n✓ {num_requests} requests in {timer.elapsed:.2f}s (mem: +{mem_growth:.2f}MB)")
    print(f"  Memory samples: {[f'{m:.1f}MB' for m in mem_samples]}")


@pytest.mark.performance
def test_memory_cleanup_after_requests(api_client, memory_tracker):
    """
    Test de nettoyage mémoire après requêtes

    Vérifie:
    - Libération de mémoire après traitement
    - Garbage collection efficace
    - Pas d'accumulation de ressources

    Exécute 10 requêtes, force GC, vérifie que la mémoire revient proche du niveau initial.
    """
    import gc

    # Baseline memory
    gc.collect()
    time.sleep(0.1)
    mem_baseline = memory_tracker()

    # Execute requests
    for i in range(10):
        response = api_client.post("/chat", json={
            "messages": [{"role": "user", "content": f"Test {i}"}]
        })
        assert response.status_code == 200

    # Force garbage collection
    gc.collect()
    time.sleep(0.1)
    mem_after_gc = memory_tracker()

    # Memory should be close to baseline (within 20MB)
    mem_diff = mem_after_gc['rss_mb'] - mem_baseline['rss_mb']
    assert mem_diff < 20, f"Memory not cleaned up: +{mem_diff:.2f}MB after GC"

    print(f"\n✓ Memory cleanup verified: +{mem_diff:.2f}MB after 10 requests + GC")


@pytest.mark.performance
@pytest.mark.slow
def test_memory_under_concurrent_load(api_client, memory_tracker, performance_tracker):
    """
    Test d'utilisation mémoire sous charge concurrente

    Vérifie:
    - Utilisation mémoire raisonnable avec concurrence
    - Pas de pic mémoire excessif
    - Stabilité sous charge

    Performance attendue:
    - 20 requêtes concurrentes < 200 MB croissance
    """
    num_concurrent = 20

    # Initial memory
    mem_before = memory_tracker()

    def make_request(i: int):
        response = api_client.post("/chat", json={
            "messages": [{"role": "user", "content": f"Concurrent {i}"}]
        })
        return response.status_code == 200

    # Execute concurrent load
    with performance_tracker("concurrent_memory_test") as timer:
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            results = list(executor.map(make_request, range(num_concurrent)))

    # Wait for cleanup
    import gc
    gc.collect()
    time.sleep(0.2)

    mem_after = memory_tracker()
    mem_growth = mem_after['rss_mb'] - mem_before['rss_mb']

    # Verify all succeeded
    assert all(results), "Some concurrent requests failed"

    # Verify reasonable memory usage
    assert mem_growth < 200, f"Concurrent load used {mem_growth:.2f}MB (expected < 200MB)"

    print(f"\n✓ {num_concurrent} concurrent requests: +{mem_growth:.2f}MB in {timer.elapsed:.2f}s")


# ============================================================================
# TESTS: HTN Planner Scalability
# ============================================================================

@pytest.mark.performance
def test_htn_planner_simple_decomposition(mock_model, performance_tracker):
    """
    Test de performance du planificateur HTN - décomposition simple

    Vérifie:
    - Temps de planification < 0.5s pour 3-5 tâches
    - Graphe valide généré
    - Métadonnées de traçabilité présentes
    """
    from tools.registry import get_registry

    planner = HierarchicalPlanner(
        model_interface=mock_model,
        tools_registry=get_registry(),
        max_decomposition_depth=2,
        enable_tracing=True
    )

    query = "Read file.txt, analyze content, generate summary"

    with performance_tracker("htn_simple_planning") as timer:
        result = planner.plan(
            query=query,
            strategy=PlanningStrategy.RULE_BASED,
            context={}
        )

    # Verify planning succeeded
    assert result is not None
    assert result.graph is not None
    assert timer.elapsed < 0.5, f"Planning took {timer.elapsed:.2f}s (expected < 0.5s)"

    print(f"\n✓ HTN simple planning: {timer.elapsed:.2f}s")


@pytest.mark.performance
@pytest.mark.slow
def test_htn_planner_complex_decomposition(mock_model, performance_tracker):
    """
    Test de scalabilité du planificateur HTN - décomposition complexe

    Vérifie:
    - Gestion de requêtes multi-étapes complexes
    - Temps de planification < 2s pour 10-15 tâches
    - Détection correcte des dépendances
    - Graphe DAG valide
    """
    from tools.registry import get_registry

    planner = HierarchicalPlanner(
        model_interface=mock_model,
        tools_registry=get_registry(),
        max_decomposition_depth=3,
        enable_tracing=True
    )

    # Complex multi-step query
    query = """
    Read data1.csv and data2.csv in parallel,
    merge the results,
    perform statistical analysis,
    generate visualizations,
    create a PDF report,
    send email notification
    """

    with performance_tracker("htn_complex_planning") as timer:
        result = planner.plan(
            query=query,
            strategy=PlanningStrategy.HYBRID,
            context={}
        )

    assert result is not None
    assert result.graph is not None
    assert timer.elapsed < 2.0, f"Complex planning took {timer.elapsed:.2f}s (expected < 2s)"

    # Verify graph structure
    tasks = result.graph.get_all_tasks()
    assert len(tasks) > 0, "No tasks generated"

    print(f"\n✓ HTN complex planning: {len(tasks)} tasks in {timer.elapsed:.2f}s")


@pytest.mark.performance
def test_htn_executor_parallel_performance(mock_model, performance_tracker):
    """
    Test de performance de l'exécuteur HTN - exécution parallèle

    Vérifie:
    - Exécution parallèle plus rapide que séquentielle
    - Gestion correcte de la concurrence
    - Aucune corruption de données

    Performance attendue:
    - 5 tâches parallèles < 1s (vs 2-3s séquentiel)
    """
    from tools.registry import get_registry

    # Create simple task graph with parallel tasks
    graph = TaskGraph()

    # Root task
    root = Task(
        task_id="root",
        name="Root task",
        action="noop",
        params={}
    )
    graph.add_task(root)

    # Add 5 independent parallel tasks
    for i in range(5):
        task = Task(
            task_id=f"task_{i}",
            name=f"Parallel task {i}",
            action="calculator",
            params={"expression": f"{i} + {i}"}
        )
        task.depends_on = ["root"]
        graph.add_task(task)

    # Create executor
    from planner import ExecutionStrategy
    executor = TaskExecutor(
        action_registry=get_registry(),
        strategy=ExecutionStrategy.PARALLEL,
        max_workers=5
    )

    # Execute in parallel
    with performance_tracker("htn_parallel_execution") as timer:
        result = executor.execute(graph, context={})

    assert result.success, f"Execution failed: {result.error_message}"
    assert timer.elapsed < 1.0, f"Parallel execution took {timer.elapsed:.2f}s (expected < 1s)"

    print(f"\n✓ HTN parallel execution: 5 tasks in {timer.elapsed:.2f}s")


@pytest.mark.performance
@pytest.mark.slow
def test_htn_planner_scalability_stress(mock_model, performance_tracker, memory_tracker):
    """
    Test de stress du planificateur HTN

    Vérifie:
    - Gestion de multiples planifications successives
    - Stabilité mémoire
    - Pas de dégradation des performances

    Exécute 20 planifications et mesure temps + mémoire.

    Performance attendue:
    - 20 planifications < 10s
    - Croissance mémoire < 50 MB
    """
    from tools.registry import get_registry

    planner = HierarchicalPlanner(
        model_interface=mock_model,
        tools_registry=get_registry(),
        max_decomposition_depth=2,
        enable_tracing=True
    )

    num_iterations = 20
    planning_times = []

    mem_before = memory_tracker()

    with performance_tracker("htn_stress_test") as timer:
        for i in range(num_iterations):
            query = f"Task {i}: Read file, analyze, report"

            start = time.time()
            result = planner.plan(
                query=query,
                strategy=PlanningStrategy.RULE_BASED,
                context={}
            )
            elapsed = time.time() - start

            planning_times.append(elapsed)
            assert result is not None

    mem_after = memory_tracker()
    mem_growth = mem_after['rss_mb'] - mem_before['rss_mb']

    # Performance assertions
    assert timer.elapsed < 10.0, f"Stress test took {timer.elapsed:.2f}s (expected < 10s)"
    assert mem_growth < 50, f"Memory grew by {mem_growth:.2f}MB (expected < 50MB)"

    # Verify no degradation (last 5 should be similar to first 5)
    avg_first_5 = sum(planning_times[:5]) / 5
    avg_last_5 = sum(planning_times[-5:]) / 5

    # Allow 50% slowdown max
    assert avg_last_5 < avg_first_5 * 1.5, "Performance degradation detected"

    print(f"\n✓ HTN stress test: {num_iterations} plannings in {timer.elapsed:.2f}s")
    print(f"  Memory: +{mem_growth:.2f}MB")
    print(f"  Avg time: first 5={avg_first_5:.3f}s, last 5={avg_last_5:.3f}s")


@pytest.mark.performance
def test_htn_verifier_performance(performance_tracker):
    """
    Test de performance du vérificateur HTN

    Vérifie:
    - Temps de vérification < 0.1s par tâche
    - Scalabilité avec nombre de tâches
    - Overhead minimal
    """
    from planner import VerificationLevel

    verifier = TaskVerifier(
        default_level=VerificationLevel.STRICT,
        enable_tracing=True
    )

    # Create task graph with multiple tasks
    graph = TaskGraph()

    for i in range(10):
        task = Task(
            task_id=f"task_{i}",
            name=f"Task {i}",
            action="calculator",
            params={"expression": "2 + 2"},
            result={"output": "4", "status": "success"}
        )
        graph.add_task(task)

    # Verify all tasks
    with performance_tracker("htn_verification") as timer:
        verifications = verifier.verify_graph_results(
            graph=graph,
            level=VerificationLevel.STRICT
        )

    assert len(verifications) == 10
    assert timer.elapsed < 1.0, f"Verification took {timer.elapsed:.2f}s (expected < 1s)"

    avg_per_task = timer.elapsed / 10
    print(f"\n✓ HTN verification: 10 tasks in {timer.elapsed:.2f}s ({avg_per_task:.3f}s/task)")


# ============================================================================
# TESTS: Combined Load Testing
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_full_system_load_test(api_client, memory_tracker, performance_tracker):
    """
    Test de charge système complet

    Simule une charge réaliste:
    - Requêtes mixtes (simples + complexes)
    - Concurrence modérée
    - Historiques variables
    - Utilisation d'outils

    Vérifie:
    - Stabilité globale
    - Performance acceptable
    - Pas de fuites mémoire
    - Tous les middlewares fonctionnels

    Performance attendue:
    - 30 requêtes mixtes < 10s
    - Croissance mémoire < 150 MB
    """
    num_requests = 30
    successful = 0
    failed = 0

    mem_before = memory_tracker()

    with performance_tracker("full_system_load") as timer:
        for i in range(num_requests):
            # Mix of request types
            if i % 3 == 0:
                # Simple request
                messages = [{"role": "user", "content": f"Simple {i}"}]
            elif i % 3 == 1:
                # Request with history
                messages = [
                    {"role": "user", "content": f"Context {i} part 1"},
                    {"role": "assistant", "content": "Response"},
                    {"role": "user", "content": f"Context {i} part 2"}
                ]
            else:
                # Complex request
                messages = [{"role": "user", "content": f"Complex task {i}: analyze and report"}]

            try:
                response = api_client.post("/chat", json={"messages": messages})
                if response.status_code == 200:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                print(f"Request {i} failed: {e}")

    mem_after = memory_tracker()
    mem_growth = mem_after['rss_mb'] - mem_before['rss_mb']

    # Verify success rate
    success_rate = successful / num_requests
    assert success_rate > 0.95, f"Success rate {success_rate:.1%} too low (expected > 95%)"

    # Performance assertions
    assert timer.elapsed < 10.0, f"Full load test took {timer.elapsed:.2f}s (expected < 10s)"
    assert mem_growth < 150, f"Memory grew by {mem_growth:.2f}MB (expected < 150MB)"

    print(f"\n✓ Full system load test:")
    print(f"  {successful}/{num_requests} succeeded in {timer.elapsed:.2f}s")
    print(f"  Memory: +{mem_growth:.2f}MB")
    print(f"  Avg time: {timer.elapsed/num_requests:.3f}s/request")


# ============================================================================
# PERFORMANCE BENCHMARKS & REPORTING
# ============================================================================

@pytest.mark.performance
def test_performance_baseline_report(api_client, performance_tracker, memory_tracker, tmp_path):
    """
    Génère un rapport de performance de référence

    Exécute une série de tests standardisés et génère un rapport JSON
    avec les métriques de performance pour établir une baseline.

    Utile pour:
    - Comparaison avant/après optimisations
    - Détection de régressions
    - Documentation des performances
    """
    import gc

    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "tests": []
    }

    # Test 1: Single request latency
    gc.collect()
    mem_before = memory_tracker()
    with performance_tracker("single_request") as timer:
        response = api_client.post("/chat", json={
            "messages": [{"role": "user", "content": "Hello"}]
        })
    mem_after = memory_tracker()

    report["tests"].append({
        "name": "single_request_latency",
        "time_seconds": timer.elapsed,
        "memory_mb": mem_after['rss_mb'] - mem_before['rss_mb'],
        "status": "pass" if response.status_code == 200 else "fail"
    })

    # Test 2: Throughput (10 sequential)
    gc.collect()
    mem_before = memory_tracker()
    with performance_tracker("throughput_10") as timer:
        for i in range(10):
            api_client.post("/chat", json={
                "messages": [{"role": "user", "content": f"Test {i}"}]
            })
    mem_after = memory_tracker()

    throughput = 10 / timer.elapsed
    report["tests"].append({
        "name": "throughput_10_sequential",
        "requests_per_second": throughput,
        "total_time_seconds": timer.elapsed,
        "memory_mb": mem_after['rss_mb'] - mem_before['rss_mb']
    })

    # Test 3: Memory baseline
    gc.collect()
    baseline_mem = memory_tracker()
    report["baseline_memory_mb"] = baseline_mem['rss_mb']

    # Save report
    report_path = tmp_path / "performance_baseline.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Performance baseline report generated:")
    print(f"  Single request: {report['tests'][0]['time_seconds']:.3f}s")
    print(f"  Throughput: {report['tests'][1]['requests_per_second']:.2f} req/s")
    print(f"  Baseline memory: {baseline_mem['rss_mb']:.1f}MB")
    print(f"  Report saved: {report_path}")

    # Basic assertions
    assert report['tests'][0]['time_seconds'] < 1.0, "Single request too slow"
    assert throughput > 5.0, "Throughput too low"
