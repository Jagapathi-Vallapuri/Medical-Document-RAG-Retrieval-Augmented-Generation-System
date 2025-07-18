"""
Environment variable validation for the RAG application
"""
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv


class EnvironmentValidator:
    """Validates required environment variables"""
    
    REQUIRED_VARS = [
        "HUGGINGFACE_API_KEY",
        "MONGO_URI", 
        "OPENAI_API_BASE"
    ]
    
    OPTIONAL_VARS = {
        "BUCKET": "pdf-storage-for-rag-1",
        "EMBEDDING_MODEL": "NeuML/pubmedbert-base-embeddings",
        "LLM_MODEL": "ii-medical-8b-1706@q4_k_m",
        "SCORE_THRESHOLD": "0.75",
        "MAX_CHUNKS": "2",
        "LOG_LEVEL": "WARNING",
        "ALLOWED_ORIGINS": "http://localhost:3000,http://localhost:5173"
    }
    
    @classmethod
    def validate(cls) -> Dict[str, str]:
        """
        Validate environment variables and return configuration
        
        Returns:
            Dict of validated environment variables
            
        Raises:
            ValueError: If required variables are missing
        """
        load_dotenv()
        
        missing_vars = []
        config = {}
        
        # Check required variables
        for var in cls.REQUIRED_VARS:
            value = os.getenv(var)
            if not value:
                missing_vars.append(var)
            else:
                config[var] = value
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
        
        # Set optional variables with defaults
        for var, default in cls.OPTIONAL_VARS.items():
            config[var] = os.getenv(var, default)
        
        return config
    
    @classmethod
    def print_config_summary(cls) -> bool:
        """
        Print a summary of the current configuration
        
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            config = cls.validate()
            print("✅ Environment Configuration Valid")
            print("=" * 40)
            
            # Print required variables (masked for security)
            for var in cls.REQUIRED_VARS:
                value = config[var]
                if "key" in var.lower() or "secret" in var.lower():
                    masked_value = f"{value[:8]}..." if len(value) > 8 else "***"
                    print(f"✓ {var}: {masked_value}")
                else:
                    print(f"✓ {var}: {value}")
            
            print("\nOptional Variables:")
            for var in cls.OPTIONAL_VARS:
                print(f"  {var}: {config[var]}")
                
        except ValueError as e:
            print(f"❌ Configuration Error: {e}")
            return False
        
        return True


if __name__ == "__main__":
    EnvironmentValidator.print_config_summary()
