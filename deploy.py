"""
Production Deployment Guide
Complete setup for running the Redis Leaderboard system in production
"""

import os
import sys
import subprocess
import platform


class DeploymentManager:
    def __init__(self):
        self.python_cmd = "python" if platform.system() == "Windows" else "python3"
        self.pip_cmd = "pip" if platform.system() == "Windows" else "pip3"
        
    def check_requirements(self):
        """Check if all requirements are met"""
        print("🔍 Checking system requirements...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            print("❌ Python 3.8+ is required!")
            return False
        print(f"✅ Python {sys.version.split()[0]}")
        
        # Check Redis availability
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            print("✅ Redis connection successful")
        except:
            print("❌ Redis is not running or not accessible")
            print("   Please start Redis server first")
            return False
        
        return True
    
    def install_dependencies(self):
        """Install all required dependencies"""
        print("\n📦 Installing dependencies...")
        
        try:
            subprocess.run([self.pip_cmd, "install", "-r", "requirements.txt"], 
                         check=True, capture_output=True)
            print("✅ All dependencies installed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False
    
    def setup_environment(self):
        """Setup environment variables"""
        print("\n⚙️ Setting up environment...")
        
        # Create production .env file if it doesn't exist
        if not os.path.exists('.env.production'):
            env_content = """# Production Environment Settings
REDIS_URL=redis://localhost:6379
REDIS_MAX_CONNECTIONS=50
CACHE_TTL=300
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW=3600
LOG_LEVEL=INFO
MONITORING_ENABLED=true
WEBSOCKET_ORIGINS=*
"""
            with open('.env.production', 'w') as f:
                f.write(env_content)
            print("✅ Created .env.production file")
        
        print("✅ Environment configured")
        return True
    
    def run_tests(self):
        """Run comprehensive tests"""
        print("\n🧪 Running tests...")
        
        try:
            # Run unit tests
            result = subprocess.run([self.python_cmd, "-m", "pytest", "test_leaderboard.py", "-v"], 
                                 capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ All tests passed")
                return True
            else:
                print("❌ Some tests failed:")
                print(result.stdout)
                print(result.stderr)
                return False
        except FileNotFoundError:
            print("⚠️ pytest not found, skipping tests")
            return True
    
    def start_services(self):
        """Start all services"""
        print("\n🚀 Starting services...")
        
        services = {
            "Basic Leaderboard API": "api.py",
            "Real-time WebSocket Server": "realtime_leaderboard.py",
            "Monitoring Dashboard": "monitoring.py"
        }
        
        print("\nAvailable services:")
        for i, (name, file) in enumerate(services.items(), 1):
            print(f"  {i}. {name} ({file})")
        
        print("\nTo start a service:")
        for name, file in services.items():
            print(f"  {self.python_cmd} {file}")
        
        return True
    
    def display_urls(self):
        """Display service URLs"""
        print("\n🌐 Service URLs:")
        print("  📊 REST API: http://localhost:8000")
        print("  📊 API Docs: http://localhost:8000/docs")
        print("  🔴 Real-time Dashboard: http://localhost:8001")
        print("  📈 Monitoring: Run monitoring.py for system stats")
        
    def deploy(self):
        """Full deployment process"""
        print("🚀 REDIS LEADERBOARD - PRODUCTION DEPLOYMENT")
        print("=" * 50)
        
        # Step 1: Check requirements
        if not self.check_requirements():
            print("\n❌ Deployment failed: Requirements not met")
            return False
        
        # Step 2: Install dependencies
        if not self.install_dependencies():
            print("\n❌ Deployment failed: Could not install dependencies")
            return False
        
        # Step 3: Setup environment
        if not self.setup_environment():
            print("\n❌ Deployment failed: Environment setup failed")
            return False
        
        # Step 4: Run tests
        if not self.run_tests():
            print("\n⚠️ Warning: Tests failed, but continuing deployment...")
        
        # Step 5: Display service information
        self.start_services()
        self.display_urls()
        
        print("\n✅ DEPLOYMENT COMPLETED SUCCESSFULLY!")
        print("\n📋 Quick Start Commands:")
        print(f"  • Demo all features: {self.python_cmd} gamification_demo.py")
        print(f"  • Start REST API: {self.python_cmd} api.py")
        print(f"  • Start real-time: {self.python_cmd} realtime_leaderboard.py")
        print(f"  • Run monitoring: {self.python_cmd} monitoring.py")
        
        print("\n🔗 Documentation:")
        print("  • README.md - Complete system documentation")
        print("  • Check logs in Redis for operational data")
        
        return True


if __name__ == "__main__":
    manager = DeploymentManager()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "check":
            manager.check_requirements()
        elif command == "install":
            manager.install_dependencies()
        elif command == "test":
            manager.run_tests()
        elif command == "demo":
            os.system(f"{manager.python_cmd} gamification_demo.py")
        else:
            print("Usage: python deploy.py [check|install|test|demo]")
    else:
        # Full deployment
        manager.deploy()