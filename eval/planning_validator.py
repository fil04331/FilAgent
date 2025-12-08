"""
Planning Evaluation Module

Provides robust validation for agent planning capabilities beyond simple
keyword matching. Validates plan structure, dependencies, and executability.
"""

from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Any
from enum import Enum
import re


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """
    Representation of a task in a plan
    
    Attributes:
        id: Unique task identifier
        name: Human-readable task name
        dependencies: Set of task IDs this task depends on
        duration: Estimated duration in seconds
        status: Current task status
    """
    id: str
    name: str
    dependencies: Set[str]
    duration: float = 0.0
    status: TaskStatus = TaskStatus.PENDING
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, Task):
            return False
        return self.id == other.id


class PlanValidator:
    """Validate the structure and executability of plans"""
    
    @staticmethod
    def parse_plan_from_text(text: str) -> List[Task]:
        """
        Parse a plan from natural language text
        
        This is a simplified parser that looks for common patterns:
        - "Step 1:", "Task A:", numbered lists, etc.
        - Dependency indicators: "after", "requires", "depends on"
        
        Args:
            text: Natural language plan text
            
        Returns:
            List of Task objects
        """
        tasks = []
        lines = text.split('\n')
        
        # Pattern to match task indicators
        task_pattern = re.compile(r'^\s*(?:(?:Step|Task|Étape)\s+(\d+|[A-Za-z])|(\d+)\.)\s*[:\-]?\s*(.+)', re.IGNORECASE)
        
        current_task_id = None
        task_counter = 0
        task_map = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            match = task_pattern.match(line)
            if match:
                task_counter += 1
                task_id = match.group(1) or match.group(2) or str(task_counter)
                task_name = match.group(3).strip()
                
                # Extract dependencies from the task name
                dependencies = PlanValidator._extract_dependencies(task_name, task_map)
                
                task = Task(
                    id=f"task_{task_id}",
                    name=task_name,
                    dependencies=dependencies,
                    duration=1.0  # Default duration
                )
                
                tasks.append(task)
                task_map[task_id] = task.id
                current_task_id = task.id
        
        # If no structured tasks found, create a simple sequential plan
        if not tasks and text.strip():
            # Look for action verbs or sequential indicators
            sentences = [s.strip() for s in re.split(r'[.!?;]', text) if s.strip()]
            
            for i, sentence in enumerate(sentences[:10]):  # Max 10 steps
                if len(sentence) > 10:  # Meaningful sentence
                    dependencies = {f"task_{i}"} if i > 0 else set()
                    tasks.append(Task(
                        id=f"task_{i+1}",
                        name=sentence,
                        dependencies=dependencies,
                        duration=1.0
                    ))
        
        return tasks
    
    @staticmethod
    def _extract_dependencies(task_name: str, task_map: Dict[str, str]) -> Set[str]:
        """Extract task dependencies from task description"""
        dependencies = set()
        
        # Look for dependency keywords
        dependency_patterns = [
            r'after\s+(?:step|task|étape)\s+(\d+|[A-Za-z])',
            r'requires?\s+(?:step|task|étape)\s+(\d+|[A-Za-z])',
            r'depends?\s+on\s+(?:step|task|étape)\s+(\d+|[A-Za-z])',
            r'dépend\s+de\s+(?:l\')?(?:étape|tâche)\s+(\d+|[A-Za-z])',
            r'après\s+(?:l\')?(?:étape|tâche)\s+(\d+|[A-Za-z])',
        ]
        
        task_name_lower = task_name.lower()
        
        for pattern in dependency_patterns:
            matches = re.finditer(pattern, task_name_lower, re.IGNORECASE)
            for match in matches:
                dep_id = match.group(1)
                if dep_id in task_map:
                    dependencies.add(task_map[dep_id])
        
        return dependencies
    
    @staticmethod
    def validate_dependencies(tasks: List[Task]) -> bool:
        """
        Validate that the task graph is a DAG (no cycles)
        
        Args:
            tasks: List of tasks to validate
            
        Returns:
            True if no cycles detected, False otherwise
        """
        if not tasks:
            return True
        
        task_dict = {task.id: task for task in tasks}
        visited = set()
        rec_stack = set()
        
        def has_cycle(task_id: str) -> bool:
            """DFS to detect cycles"""
            visited.add(task_id)
            rec_stack.add(task_id)
            
            task = task_dict.get(task_id)
            if not task:
                rec_stack.remove(task_id)
                return False
            
            for dep_id in task.dependencies:
                if dep_id not in visited:
                    if has_cycle(dep_id):
                        return True
                elif dep_id in rec_stack:
                    # Found a cycle
                    return True
            
            rec_stack.remove(task_id)
            return False
        
        # Check all tasks
        for task in tasks:
            if task.id not in visited:
                if has_cycle(task.id):
                    return False
        
        return True
    
    @staticmethod
    def validate_topological_order(tasks: List[Task]) -> bool:
        """
        Validate that tasks are in topological order
        
        Each task should appear after all its dependencies
        
        Args:
            tasks: List of tasks (order matters)
            
        Returns:
            True if order is valid, False otherwise
        """
        task_positions = {task.id: i for i, task in enumerate(tasks)}
        
        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id in task_positions:
                    if task_positions[dep_id] >= task_positions[task.id]:
                        # Dependency comes after the task - invalid order
                        return False
        
        return True
    
    @staticmethod
    def simulate_execution(tasks: List[Task]) -> Dict[str, Any]:
        """
        Simulate execution of a plan
        
        Checks if the plan is executable by simulating topological execution
        
        Args:
            tasks: List of tasks to execute
            
        Returns:
            Execution simulation results with success status and metrics
        """
        if not tasks:
            return {
                'success': False,
                'error': 'empty_plan',
                'completed': set()
            }
        
        completed = set()
        total_duration = 0.0
        max_iterations = len(tasks) * 2  # Prevent infinite loops
        iteration = 0
        
        # Create task lookup
        task_dict = {task.id: task for task in tasks}
        
        while len(completed) < len(tasks) and iteration < max_iterations:
            iteration += 1
            found_ready = False
            
            for task in tasks:
                if task.id not in completed:
                    # Check if all dependencies are satisfied
                    if task.dependencies.issubset(completed):
                        # Task is ready to execute
                        completed.add(task.id)
                        total_duration += task.duration
                        found_ready = True
            
            if not found_ready and len(completed) < len(tasks):
                # No progress made - deadlock
                incomplete = [t.id for t in tasks if t.id not in completed]
                return {
                    'success': False,
                    'error': 'deadlock',
                    'completed': completed,
                    'incomplete': incomplete,
                    'total_duration': total_duration
                }
        
        if len(completed) < len(tasks):
            return {
                'success': False,
                'error': 'max_iterations',
                'completed': completed,
                'total_duration': total_duration
            }
        
        return {
            'success': True,
            'completed': completed,
            'total_duration': total_duration,
            'task_count': len(tasks)
        }
    
    @staticmethod
    def analyze_plan_quality(tasks: List[Task]) -> Dict[str, Any]:
        """
        Analyze the quality of a plan
        
        Checks various quality metrics:
        - Plan size (too small or too large?)
        - Dependency complexity
        - Parallelization opportunities
        
        Args:
            tasks: List of tasks in the plan
            
        Returns:
            Quality analysis metrics
        """
        if not tasks:
            return {
                'valid': False,
                'reason': 'empty_plan'
            }
        
        # Basic metrics
        task_count = len(tasks)
        total_dependencies = sum(len(task.dependencies) for task in tasks)
        avg_dependencies = total_dependencies / task_count if task_count > 0 else 0
        
        # Find tasks that can run in parallel
        task_levels = PlanValidator._compute_task_levels(tasks)
        max_level = max(task_levels.values()) if task_levels else 0
        parallel_opportunities = task_count - max_level if max_level > 0 else 0
        
        # Quality checks
        issues = []
        
        if task_count < 2:
            issues.append("Plan too simple (< 2 tasks)")
        
        if task_count > 100:
            issues.append("Plan too complex (> 100 tasks)")
        
        if avg_dependencies > 5:
            issues.append("Too many dependencies per task")
        
        return {
            'valid': len(issues) == 0,
            'task_count': task_count,
            'total_dependencies': total_dependencies,
            'avg_dependencies': avg_dependencies,
            'max_depth': max_level,
            'parallel_opportunities': parallel_opportunities,
            'issues': issues
        }
    
    @staticmethod
    def _compute_task_levels(tasks: List[Task]) -> Dict[str, int]:
        """
        Compute the execution level of each task
        
        Level 0 = no dependencies
        Level N = max(dependency levels) + 1
        """
        task_dict = {task.id: task for task in tasks}
        levels = {}
        
        def compute_level(task_id: str) -> int:
            if task_id in levels:
                return levels[task_id]
            
            task = task_dict.get(task_id)
            if not task or not task.dependencies:
                levels[task_id] = 0
                return 0
            
            max_dep_level = max(compute_level(dep_id) for dep_id in task.dependencies if dep_id in task_dict)
            levels[task_id] = max_dep_level + 1
            return levels[task_id]
        
        for task in tasks:
            compute_level(task.id)
        
        return levels


def evaluate_planning_capability(plan_text: str) -> Dict[str, Any]:
    """
    Comprehensive evaluation of planning capability
    
    Args:
        plan_text: Natural language plan to evaluate
        
    Returns:
        Evaluation results with detailed metrics
    """
    # 1. Parse the plan
    tasks = PlanValidator.parse_plan_from_text(plan_text)
    
    if not tasks:
        return {
            'passed': False,
            'error': 'No tasks found in plan',
            'tasks': []
        }
    
    # 2. Validate dependencies (no cycles)
    valid_dependencies = PlanValidator.validate_dependencies(tasks)
    if not valid_dependencies:
        return {
            'passed': False,
            'error': 'Plan contains circular dependencies',
            'tasks': [{'id': t.id, 'name': t.name} for t in tasks]
        }
    
    # 3. Validate topological order
    valid_order = PlanValidator.validate_topological_order(tasks)
    if not valid_order:
        return {
            'passed': False,
            'error': 'Tasks not in valid topological order',
            'tasks': [{'id': t.id, 'name': t.name} for t in tasks]
        }
    
    # 4. Simulate execution
    execution = PlanValidator.simulate_execution(tasks)
    if not execution['success']:
        return {
            'passed': False,
            'error': f"Plan execution failed: {execution.get('error')}",
            'tasks': [{'id': t.id, 'name': t.name} for t in tasks],
            'execution': execution
        }
    
    # 5. Analyze quality
    quality = PlanValidator.analyze_plan_quality(tasks)
    
    return {
        'passed': quality['valid'],
        'tasks': [{'id': t.id, 'name': t.name, 'dependencies': list(t.dependencies)} for t in tasks],
        'execution': execution,
        'quality': quality
    }
