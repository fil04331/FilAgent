"""
Unit tests for evaluation target and planning validators

Tests the data-driven evaluation system added in Phase 3.
"""

import pytest
from pathlib import Path
import tempfile
import yaml

from eval.target_validator import (
    EvaluationTarget,
    EvaluationTargetLoader,
    TargetValidator,
    ComparisonOperator
)
from eval.planning_validator import (
    Task,
    PlanValidator,
    evaluate_planning_capability
)


class TestEvaluationTarget:
    """Tests for EvaluationTarget dataclass"""
    
    def test_valid_target_creation(self):
        """Test creating a valid target"""
        target = EvaluationTarget(
            benchmark="humaneval",
            metric="pass_rate",
            operator=">=",
            value=0.65,
            description="Test target"
        )
        
        assert target.benchmark == "humaneval"
        assert target.metric == "pass_rate"
        assert target.operator == ">="
        assert target.value == 0.65
    
    def test_invalid_operator_raises_error(self):
        """Test that invalid operator raises ValueError"""
        with pytest.raises(ValueError, match="Invalid operator"):
            EvaluationTarget(
                benchmark="test",
                metric="score",
                operator=">>",  # Invalid
                value=50
            )


class TestEvaluationTargetLoader:
    """Tests for EvaluationTargetLoader"""
    
    def test_load_targets_from_yaml(self):
        """Test loading targets from YAML file"""
        # Create a temporary YAML file
        config = {
            'targets': [
                {
                    'benchmark': 'humaneval',
                    'metric': 'pass_rate',
                    'operator': '>=',
                    'value': 0.65,
                    'description': 'HumanEval baseline'
                },
                {
                    'benchmark': 'compliance',
                    'metric': 'dr_coverage',
                    'operator': '==',
                    'value': 100,
                    'description': 'Decision Record coverage'
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            temp_path = f.name
        
        try:
            targets = EvaluationTargetLoader.load_targets(temp_path)
            
            assert len(targets) == 2
            assert targets[0].benchmark == 'humaneval'
            assert targets[1].benchmark == 'compliance'
        finally:
            Path(temp_path).unlink()
    
    def test_load_targets_file_not_found(self):
        """Test that FileNotFoundError is raised for missing config"""
        with pytest.raises(FileNotFoundError):
            EvaluationTargetLoader.load_targets("nonexistent.yaml")
    
    def test_load_targets_from_benchmarks_format(self):
        """Test loading from benchmarks-structured config"""
        config = {
            'benchmarks': {
                'humaneval': {
                    'enabled': True,
                    'pass_at_1': 0.65,
                    'pass_at_10': 0.85
                },
                'mbpp': {
                    'enabled': True,
                    'pass_at_1': 0.60
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            temp_path = f.name
        
        try:
            targets = EvaluationTargetLoader.load_targets(temp_path)
            
            assert len(targets) >= 3
            # Check that targets were created from benchmarks
            benchmark_names = {t.benchmark for t in targets}
            assert 'humaneval' in benchmark_names
            assert 'mbpp' in benchmark_names
        finally:
            Path(temp_path).unlink()


class TestTargetValidator:
    """Tests for TargetValidator"""
    
    def test_validate_all_passing(self):
        """Test validation when all targets pass"""
        targets = [
            EvaluationTarget("humaneval", "pass_rate", ">=", 0.65),
            EvaluationTarget("mbpp", "pass_rate", ">=", 0.60)
        ]
        
        results = {
            "humaneval": {"pass_rate": 0.70},
            "mbpp": {"pass_rate": 0.65}
        }
        
        validator = TargetValidator(targets)
        validation = validator.validate(results)
        
        assert validation['passed'] is True
        assert validation['passed_count'] == 2
        assert validation['total_count'] == 2
    
    def test_validate_some_failing(self):
        """Test validation when some targets fail"""
        targets = [
            EvaluationTarget("humaneval", "pass_rate", ">=", 0.65),
            EvaluationTarget("mbpp", "pass_rate", ">=", 0.60)
        ]
        
        results = {
            "humaneval": {"pass_rate": 0.70},
            "mbpp": {"pass_rate": 0.55}  # Below target
        }
        
        validator = TargetValidator(targets)
        validation = validator.validate(results)
        
        assert validation['passed'] is False
        assert validation['passed_count'] == 1
        assert validation['total_count'] == 2
    
    def test_validate_missing_metric(self):
        """Test validation when metric is missing"""
        targets = [
            EvaluationTarget("humaneval", "pass_rate", ">=", 0.65)
        ]
        
        results = {
            "humaneval": {"other_metric": 0.70}  # Missing pass_rate
        }
        
        validator = TargetValidator(targets)
        validation = validator.validate(results)
        
        assert validation['passed'] is False
        assert validation['results'][0]['current_value'] is None


class TestPlanValidator:
    """Tests for PlanValidator"""
    
    def test_parse_simple_plan(self):
        """Test parsing a simple sequential plan"""
        plan_text = """
        Step 1: Read the file
        Step 2: Process the data
        Step 3: Generate report
        """
        
        tasks = PlanValidator.parse_plan_from_text(plan_text)
        
        assert len(tasks) >= 3
        assert tasks[0].name.lower().find('read') >= 0
    
    def test_validate_dependencies_no_cycle(self):
        """Test that DAG validation passes for acyclic graph"""
        tasks = [
            Task("task1", "First task", set()),
            Task("task2", "Second task", {"task1"}),
            Task("task3", "Third task", {"task2"})
        ]
        
        assert PlanValidator.validate_dependencies(tasks) is True
    
    def test_validate_dependencies_with_cycle(self):
        """Test that DAG validation fails for cyclic graph"""
        tasks = [
            Task("task1", "First task", {"task2"}),  # Depends on task2
            Task("task2", "Second task", {"task1"})  # Depends on task1 - CYCLE!
        ]
        
        assert PlanValidator.validate_dependencies(tasks) is False
    
    def test_validate_topological_order_valid(self):
        """Test topological order validation with valid order"""
        tasks = [
            Task("task1", "First", set()),
            Task("task2", "Second", {"task1"}),
            Task("task3", "Third", {"task2"})
        ]
        
        assert PlanValidator.validate_topological_order(tasks) is True
    
    def test_validate_topological_order_invalid(self):
        """Test topological order validation with invalid order"""
        tasks = [
            Task("task2", "Second", {"task1"}),  # Depends on task1
            Task("task1", "First", set()),        # But task1 comes after!
        ]
        
        assert PlanValidator.validate_topological_order(tasks) is False
    
    def test_simulate_execution_success(self):
        """Test successful execution simulation"""
        tasks = [
            Task("task1", "First", set()),
            Task("task2", "Second", {"task1"}),
            Task("task3", "Third", {"task2"})
        ]
        
        result = PlanValidator.simulate_execution(tasks)
        
        assert result['success'] is True
        assert len(result['completed']) == 3
    
    def test_simulate_execution_deadlock(self):
        """Test execution simulation with deadlock"""
        tasks = [
            Task("task1", "First", {"task2"}),
            Task("task2", "Second", {"task1"})
        ]
        
        result = PlanValidator.simulate_execution(tasks)
        
        assert result['success'] is False
        assert result['error'] == 'deadlock'


class TestEvaluatePlanningCapability:
    """Tests for the high-level planning evaluation function"""
    
    def test_evaluate_valid_plan(self):
        """Test evaluating a valid multi-step plan"""
        plan_text = """
        Step 1: Analyze the requirements
        Step 2: Design the solution
        Step 3: Implement the code
        Step 4: Test the implementation
        """
        
        result = evaluate_planning_capability(plan_text)
        
        assert result['passed'] is True
        assert len(result['tasks']) >= 2
        assert 'quality' in result
    
    def test_evaluate_empty_plan(self):
        """Test evaluating an empty plan"""
        result = evaluate_planning_capability("")
        
        assert result['passed'] is False
        assert 'error' in result
    
    def test_evaluate_single_task_plan(self):
        """Test that single-task plan fails (too simple)"""
        plan_text = "Just do the thing"
        
        result = evaluate_planning_capability(plan_text)
        
        # Should fail because plan too simple
        assert result['passed'] is False


@pytest.mark.integration
class TestIntegration:
    """Integration tests combining multiple components"""
    
    def test_end_to_end_validation(self):
        """Test complete validation flow"""
        # Create targets
        targets = [
            EvaluationTarget("test_bench", "score", ">=", 75.0)
        ]
        
        # Create results
        results = {
            "test_bench": {"score": 80.0}
        }
        
        # Validate
        validator = TargetValidator(targets)
        validation = validator.validate(results)
        
        assert validation['passed'] is True
        assert validation['pass_rate'] == 1.0
