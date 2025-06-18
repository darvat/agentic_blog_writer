# Configuration Fix and Best Practices

## Issue Resolved

Fixed an `AttributeError` in the research workflow caused by a naming conflict between the workflow's configuration object and the global application configuration.

### Error Details
```python
AttributeError: 'ArticleCreationWorkflowConfig' object has no attribute 'RESEARCH_STRATEGY'
```

### Root Cause
The workflow was trying to access `config.RESEARCH_STRATEGY` where `config` referred to the workflow's configuration object (`ArticleCreationWorkflowConfig`) instead of the global application configuration.

### Solution
1. **Fixed Import**: Changed import to avoid naming conflict
   ```python
   # Before (problematic)
   from app.core.config import config
   
   # After (fixed)
   from app.core.config import config as app_config
   ```

2. **Updated References**: Changed all references to use the correct config object
   ```python
   # Before
   if config.RESEARCH_STRATEGY == "batch":
   
   # After  
   if app_config.RESEARCH_STRATEGY == "batch":
   ```

3. **Environment Variable Cleanup**: Removed problematic environment variable that contained comments
   ```bash
   # The environment variable was set incorrectly with comments
   RESEARCH_STRATEGY="individual # or batch"
   
   # Should be clean
   RESEARCH_STRATEGY="individual"
   ```

## Configuration Best Practices

### Environment Variables
- Keep environment variable values clean (no comments)
- Use simple string values
- Avoid special characters unless necessary

### Naming Conventions
- Use descriptive import aliases to avoid conflicts
- Global config: `app_config` or `global_config`  
- Workflow config: `workflow_config` or `self.config`

### Testing Configuration
Test configuration loading with:
```python
from app.core.config import config as app_config
print(f"Strategy: {repr(app_config.RESEARCH_STRATEGY)}")
```

The `repr()` function helps identify hidden characters or unexpected values.

## Current Configuration Options

### Research Strategy
```bash
# Use individual section processing (recommended)
RESEARCH_STRATEGY=individual

# Use batch processing (original approach)
RESEARCH_STRATEGY=batch
```

### Retry Configuration
```bash
# Set number of retries for failed sections
RESEARCH_MAX_RETRIES=2
```

## Verification
After making configuration changes, verify with:
```bash
python3 -c "from app.core.config import config; print(f'Strategy: {config.RESEARCH_STRATEGY}'); print(f'Retries: {config.RESEARCH_MAX_RETRIES}')"
```

The research workflow should now run without configuration errors. 