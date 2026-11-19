"""
Program Intelligence & Curriculum Engine for Scaler Program Evaluator
Provides official catalogue URLs, track-specific structured curriculum modules,
and deep-dive syllabus outlines tailored to each learner's recommended track.
"""

# Official Scaler Program Catalog & Base Metadata
PROGRAM_CATALOG_DATA = {
    'P1_ACADEMY': {
        'program_name': 'Modern Software & AI Engineering (Scaler Academy)',
        'catalogue_url': 'https://d2beiqkhq929f0.cloudfront.net/public_assets/assets/000/218/970/original/Academy_brochure_2026_%281%29.pdf?1787132291',
        'top_hiring_companies': [
            'Amazon', 'Microsoft', 'Google', 'Razorpay', 'Swiggy', 
            'PayPal', 'Atlassian', 'Walmart', 'PhonePe', 'Salesforce'
        ]
    },
    'P2_DSML': {
        'program_name': 'Modern Data Science & Machine Learning (AI Specialization)',
        'catalogue_url': 'https://d2beiqkhq929f0.cloudfront.net/public_assets/assets/000/210/531/original/DSML_Brochure_2026_%282%29.pdf?1783928557',
        'top_hiring_companies': [
            'Amazon', 'Flipkart', 'PayPal', 'Sigmoid', 'Fractal', 
            'Mu Sigma', 'Quantiphi', 'Deloitte', 'Accenture', 'Tredence'
        ],
        'curriculum_modules': [
            {
                'segment': 'Data Analytics & SQL',
                'type': 'Core',
                'phase': 'Phase 1: Python, Advanced SQL & Data Wrangling',
                'duration': '10 Weeks',
                'topics': 'Pandas, NumPy, Advanced SQL (Window Functions, CTEs, Pivots), Data Cleaning, Exploratory Data Analysis (EDA).',
                'deliverable': 'Execute business analytics queries across 10M+ transaction tables with sub-second execution.'
            },
            {
                'segment': 'Mathematical Foundations',
                'type': 'Core',
                'phase': 'Phase 2: Applied Statistics & Probability for AI',
                'duration': '8 Weeks',
                'topics': 'Inferential Statistics, Probability Distributions, Hypothesis Testing, A/B Testing Frameworks, Regression Modeling.',
                'deliverable': 'Design statistical experiment pipelines evaluated by product companies for business impact.'
            },
            {
                'segment': 'Machine Learning',
                'type': 'Core',
                'phase': 'Phase 3: Supervised, Unsupervised & Deep Learning',
                'duration': '12 Weeks',
                'topics': 'Scikit-Learn, XGBoost, Random Forests, PyTorch, Neural Architectures, CNNs, RNNs, NLP Fundamentals.',
                'deliverable': 'Train and tune production recommendation and predictive risk scoring models.'
            },
            {
                'segment': 'Generative AI & MLOps',
                'type': 'Specialisation',
                'phase': 'Phase 4: Generative AI, LLMs & Production MLOps',
                'duration': '8 Weeks',
                'topics': 'LangChain, Vector DBs (Chroma/Pinecone), Retrieval-Augmented Generation (RAG), Model Serving (FastAPI, Docker, AWS).',
                'deliverable': 'Deploy end-to-end Enterprise RAG Question-Answering Bot on AWS.'
            }
        ]
    },
    'P3_FDE': {
        'program_name': 'AI Forward Deployed Engineer (FDE) Program',
        'catalogue_url': 'https://d2beiqkhq929f0.cloudfront.net/public_assets/assets/000/217/310/original/FDE_Brochure_.pdf?1786110990',
        'top_hiring_companies': ['Palantir', 'Fractal', 'Tiger Analytics', 'Accenture AI', 'EY Tech', 'KPMG Lighthouse']
    },
    'P4_AIML_AGENTIC': {
        'program_name': 'AI & Machine Learning with Agentic AI Program',
        'catalogue_url': 'https://d2beiqkhq929f0.cloudfront.net/public_assets/assets/000/207/098/original/AI__ML_Agentic_AI_Brochure_.pdf?1782394058',
        'top_hiring_companies': ['Google DeepMind Ecosystem', 'Microsoft Research', 'NVIDIA', 'Siemens Healthineers', 'Zoho AI']
    },
    'P5_DEVOPS_CLOUD': {
        'program_name': 'DevOps, Cloud & AI Platform Engineering',
        'catalogue_url': 'https://d2beiqkhq929f0.cloudfront.net/public_assets/assets/000/206/970/original/DEVOPS-Brochure-2026_%281%29.pdf?1782371159',
        'top_hiring_companies': ['Cisco', 'NetApp', 'AWS', 'VMware', 'Red Hat', 'BrowserStack']
    }
}

# ==============================================================================
# SOFTWARE & AI ENGINEERING (SCALER ACADEMY) - TRACK SPECIFIC DETAILED CURRICULA
# ==============================================================================

# 1. BEGINNERS TRACK (Includes Programming Fundamentals with AI)
P1_ACADEMY_BEGINNER_MODULES = [
    {
        'segment': 'Programming Fundamentals',
        'type': 'Core',
        'phase': 'Programming Fundamentals - Thinking with AI: Logics, Loops & Control Flow',
        'duration': '1 Month',
        'topics': 'Programming Foundations & AI Awareness, Operators & Expression Evaluation using AI, Data Types 1 & 2 + Reading Inputs, If-Else & AI Edge Case Thinking, Lab Session on If-Else, Loops & Iteration Analysis by AI, Lab Session on Loop, More problems on Loops & Patterns, Lab Session on Patterns, Dual Camera Proctoring, Data Types, If-Else & Loops Contest discussion.',
        'deliverable': 'Mastery of foundational computational logic, edge case handling, and AI-assisted debugging loops.'
    },
    {
        'segment': 'Programming Fundamentals',
        'type': 'Core',
        'phase': 'Programming Fundamentals - Code Smarter with AI: Function & Arrays',
        'duration': '1 Month',
        'topics': 'Functions & Modularity: Designing Code with AI, Lab Session on Functions, Introduction to Strings, 1D Array, Lab Session on 1D Array (1 & 2), 2D Array (1 & 2), Strings in Memory: Visualizing with AI, Maths Basics & Calculate Iterations, Language Internals, Contest 2: Functions & Arrays.',
        'deliverable': 'Multi-dimensional array manipulation, memory layout tracing, and clean modular function architecture.'
    },
    {
        'segment': 'Programming Fundamentals',
        'type': 'Core',
        'phase': 'Intermediate DSA : AI Assisted Problem Solving',
        'duration': '1 Month',
        'topics': 'Time Complexity, Arrays & Basics of AI, Lab Session on TC/SC/Output & Debugging, Prefix Sum & Carry Forward with AI-Assisted Problem Solving, Arrays techniques & smart prompting, Memory Management & Sorting Basics, Bit Manipulation Basics, 2D Matrices, Strings & Immutability visualisations through AI, Contest.',
        'deliverable': 'Master prefix sum patterns, bit manipulation, time/space complexity optimization, and fast matrix operations.'
    },
    {
        'segment': 'Agentic AI',
        'type': 'Core',
        'phase': 'AI & Agents: From Talking to AI to Building One',
        'duration': '1 Month',
        'topics': 'GenAI World & LLM Landscape, Prompt Engineering Basics, Advanced Prompting & AI Safety Basics, LLM Built-in Power Tools, RAG Architectures, n8n Automation Workflows, What Is an AI Agent?, Building Agents with n8n, OpenClaw: Personal 24/7 AI Agent, Multi-Agent Systems, Debugging AI.',
        'deliverable': 'Deploy autonomous multi-agent developer workflows with n8n and build a personal 24/7 AI agent.'
    },
    {
        'segment': 'Advanced DSA',
        'type': 'Core',
        'phase': 'Advanced DSA: Foundations: Core Techniques & Optimization',
        'duration': '1 Month',
        'topics': 'Time Complexity, Arrays Techniques (1D & 2D), Bit Manipulation, Recursion & Backtracking Prep, Maths: Modular Arithmetic & GCD, Hashing, Sorting (Count Sort, Merge Sort, Quick Sort & Comparator Problems), Sample Contest & Contest 1.',
        'deliverable': 'Algorithmic problem-solving foundations, recursive tree modeling, and custom comparator sorting mastery.'
    },
    {
        'segment': 'Advanced DSA',
        'type': 'Core',
        'phase': 'Advanced DSA: Linear & Non-Linear Structures',
        'duration': '1 Month',
        'topics': 'Searching 1 (Binary Search on Array) & Searching 2 (Binary Search on Answer), Classes/Objects & Linked List Intro, Linked List Basic Problems, Stacks, Queues: Implementation & Problems, Trees 1 (Structure & Traversal), Trees 2 (BST), Contest 2.',
        'deliverable': 'Production implementation of custom Linked Lists, Stacks, Queues, and Binary Search Tree traversal engines.'
    },
    {
        'segment': 'Advanced DSA',
        'type': 'Core',
        'phase': 'Advanced DSA: Backtracking & Advanced Trees',
        'duration': '1 Month',
        'topics': 'Combinatorics Basics & Prime Numbers, Lab Session on Prime Numbers & 2 Pointers, Backtracking, Linked List Sorting, Doubly Linked List & Detecting Loops, Trees 4: Morris Inorder Traversal + LCA, Hashing 3: Internal Implementation, Contest 3.',
        'deliverable': 'Solve complex backtracking constraints, tree LCA, and Morris traversal with zero auxiliary space overhead.'
    },
    {
        'segment': 'Advanced DSA',
        'type': 'Core',
        'phase': 'Advanced DSA: DP, Heaps & Graphs - Crack It with AI Edge',
        'duration': '1 Month',
        'topics': 'Heaps & Heap Sort, Greedy Algorithms, Dynamic Programming (1D, 2D, Knapsack), Graphs 1 (DFS & Cycle Detection), Graphs 2 (BFS & MST), Graphs 3 (Dijkstra Algo & Topological Sort), Social Network Analyzer Capstone, Invoice Merger Capstone, Mandatory Skill Evaluation Test.',
        'deliverable': 'Production Capstones: Social Network Graph Analyzer & Invoice Merger; full graph traversal & dynamic programming.'
    },
    {
        'segment': 'Databases & SQL',
        'type': 'Core',
        'phase': 'Databases & SQL: Production Schema Design & Optimization',
        'duration': '1 Month',
        'topics': 'Introduction to DBMS & Keys, CRUD Operations (1 & 2), Joins, Aggregate Queries, Subqueries & Views, Indexing, Transactions & Isolation, Window Functions, Schema Design (1 & 2), Databases & SQL Contest.',
        'deliverable': 'Design ACID-compliant normalized relational database schemas with high-speed indexing & window queries.'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Specialisation',
        'phase': 'Foundations of Object-Oriented Design & Scalable Systems',
        'duration': '1 Month',
        'topics': 'Intro to LLD for Scalable & AI-Ready Systems, OOP Lab (Access Modifiers, Constructors, Inheritance, Polymorphism, Interfaces, Abstract Classes), Concurrency (Threads, Executors, Callables, Synchronization, Semaphores), Java Advanced Concepts (Generics, Collections, Streams, Lambdas, Exception Handling), Contest 1.',
        'deliverable': 'Multi-threaded thread-safe concurrent in-memory caching and messaging primitives.'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Specialisation',
        'phase': 'Design Principles & Patterns for Extensible Systems',
        'duration': '1 Month',
        'topics': 'SOLID Principles with AI integrations, Creational Patterns (Singleton, Builder, Prototype/Registry, Factory for Service Abstraction), Structural Patterns (Adapter, Facade, Decorator, Flyweight), Behavioural Patterns, UML Diagrams, Contest 2.',
        'deliverable': 'Architectural design blueprints conforming to strict SOLID principles and GoF design patterns.'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Specialisation',
        'phase': 'Applied Design & Machine Coding',
        'duration': '1 Month',
        'topics': 'Machine Coding Strategies under timed conditions, Design & Implement: TicTacToe (1 & 2), Parking Lot, BookMyShow (1, 2, 3), Splitwise (1 & 2), Machine Coding Evaluations.',
        'deliverable': 'Build complete, working, object-oriented machine-coded systems (Parking Lot, Splitwise, BookMyShow).'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Specialisation',
        'phase': 'AI-First Backend Capstone Project Primer',
        'duration': '1 Month',
        'topics': 'Intro to Backend Systems & AI-Augmented Development, Version Control & Git, Spring Framework & Building APIs, MVC & Microservices with AI Service Integration, 3rd Party APIs & LLM Services, Spring Data JPA, Automated Unit Testing, OAuth2 & JWT Security, AWS Cloud Deployment.',
        'deliverable': 'Live Spring Boot microservice deployed to AWS with AI service integration and automated authentication.'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Elective',
        'phase': 'AI-First Backend Capstone Advance & Build a Production-Ready AI System',
        'duration': '1.5 - 2.5 Months',
        'topics': 'RestTemplate Resilience, Mocking & Unit Tests, OAuth2, AWS (EBS, RDS, VPC, Route 53), Semantic Search, Stripe Payments & Reconciliation, Redis Caching & Kafka Queues, Spring Cloud, Docker, BookMyShow Chat Agent, Splitwise AI Receipt Processor.',
        'deliverable': 'Enterprise-grade microservices suite with Redis caching, Kafka streaming, and autonomous AI agents.'
    },
    {
        'segment': 'Fullstack Track',
        'type': 'Specialisation',
        'phase': 'Fullstack Web Platform, React & Backend Systems (Alternative Specialisation)',
        'duration': '4 Months',
        'topics': 'Web Platform Foundations (HTML5, Responsive CSS, Flexbox/Grid), JavaScript Runtime Systems (DOM, Async/Await, Event Loop, Weather & Kanban Apps), React & Redux Product Architecture (IMDB Clone), Node.js, Express & MongoDB Production Systems.',
        'deliverable': 'Production MERN stack platform with real-time seat reservation engine and Redux state architecture.'
    },
    {
        'segment': 'System Design & Electives',
        'type': 'Elective',
        'phase': 'Distributed System Design & AI-Integrated Architectures',
        'duration': '1.5 Months',
        'topics': 'Load Balancing, Consistent Hashing, CDN & Caching at Scale (Scaler Judge, FB News Feed), CAP/PACELC Theorem, Master-Slave Replication, SQL vs NoSQL, Database Sharding, Case Studies: Google Typeahead, Messaging Apps (WhatsApp, FB Messenger), Apache Kafka, ElasticSearch, S3/HDFS, Uber Nearest Neighbor, Rate Limiter, OTT Microservices.',
        'deliverable': 'Distributed systems architecture handling 1M+ RPS with high availability and resilience.'
    },
    {
        'segment': 'Interview Prep & Electives',
        'type': 'Elective',
        'phase': 'Mastering LastMile Simulation, Data Engineering & Gen AI Electives',
        'duration': '1.5 Weeks - 2 Months',
        'topics': 'DSA/LLD/HLD Interview Simulation under pressure, Data Engineering (PySpark, Hadoop, Hive, Spark Streaming, AWS), DSA Edge (Advanced Patterns), Product Management for Engineers, Gen AI for Software Engineers (RAG, Agents, Fine-Tuning, Quantization).',
        'deliverable': 'MAANG interview clearance readiness, high-throughput data pipelines, and production generative AI systems.'
    }
]

# 2. INTERMEDIATE TRACK (Skips Beginner Programming Fundamentals; starts at Intermediate DSA)
P1_ACADEMY_INTERMEDIATE_MODULES = [
    {
        'segment': 'Programming Fundamentals',
        'type': 'Core',
        'phase': 'Intermediate DSA : AI Assisted Problem Solving',
        'duration': '1 Month',
        'topics': 'Time Complexity, Arrays & Basics of AI, Lab Session on TC/SC/Output & Debugging, Prefix Sum & Carry Forward with AI-Assisted Problem Solving, Arrays techniques & smart prompting, Memory Management & Sorting Basics, Bit Manipulation Basics, 2D Matrices, Strings & Immutability visualisations through AI, Contest.',
        'deliverable': 'Master prefix sum patterns, bit manipulation, time/space complexity optimization, and fast matrix operations.'
    },
    {
        'segment': 'Agentic AI',
        'type': 'Core',
        'phase': 'AI & Agents: From Talking to AI to Building One',
        'duration': '1 Month',
        'topics': 'GenAI World & LLM Landscape, Prompt Engineering Basics, Advanced Prompting & AI Safety Basics, LLM Built-in Power Tools, RAG Architectures, n8n Automation Workflows, What Is an AI Agent?, Building Agents with n8n, OpenClaw: Personal 24/7 AI Agent, Multi-Agent Systems, Debugging AI.',
        'deliverable': 'Deploy autonomous multi-agent developer workflows with n8n and build a personal 24/7 AI agent.'
    },
    {
        'segment': 'Advanced DSA',
        'type': 'Core',
        'phase': 'Advanced DSA: Foundations: Core Techniques & Optimization',
        'duration': '1 Month',
        'topics': 'Time Complexity, Arrays Techniques (1D & 2D), Bit Manipulation, Recursion & Backtracking Prep, Maths: Modular Arithmetic & GCD, Hashing, Sorting (Count Sort, Merge Sort, Quick Sort & Comparator Problems), Sample Contest & Contest 1.',
        'deliverable': 'Algorithmic problem-solving foundations, recursive tree modeling, and custom comparator sorting mastery.'
    },
    {
        'segment': 'Advanced DSA',
        'type': 'Core',
        'phase': 'Advanced DSA: Linear & Non-Linear Structures',
        'duration': '1 Month',
        'topics': 'Searching 1 (Binary Search on Array) & Searching 2 (Binary Search on Answer), Classes/Objects & Linked List Intro, Linked List Basic Problems, Stacks, Queues: Implementation & Problems, Trees 1 (Structure & Traversal), Trees 2 (BST), Contest 2.',
        'deliverable': 'Production implementation of custom Linked Lists, Stacks, Queues, and Binary Search Tree traversal engines.'
    },
    {
        'segment': 'Advanced DSA',
        'type': 'Core',
        'phase': 'Advanced DSA: Backtracking & Advanced Trees',
        'duration': '1 Month',
        'topics': 'Combinatorics Basics & Prime Numbers, Lab Session on Prime Numbers & 2 Pointers, Backtracking, Linked List Sorting, Doubly Linked List & Detecting Loops, Trees 4: Morris Inorder Traversal + LCA, Hashing 3: Internal Implementation, Contest 3.',
        'deliverable': 'Solve complex backtracking constraints, tree LCA, and Morris traversal with zero auxiliary space overhead.'
    },
    {
        'segment': 'Advanced DSA',
        'type': 'Core',
        'phase': 'Advanced DSA: DP, Heaps & Graphs - Crack It with AI Edge',
        'duration': '1 Month',
        'topics': 'Heaps & Heap Sort, Greedy Algorithms, Dynamic Programming (1D, 2D, Knapsack), Graphs 1 (DFS & Cycle Detection), Graphs 2 (BFS & MST), Graphs 3 (Dijkstra Algo & Topological Sort), Social Network Analyzer Capstone, Invoice Merger Capstone, Mandatory Skill Evaluation Test.',
        'deliverable': 'Production Capstones: Social Network Graph Analyzer & Invoice Merger; full graph traversal & dynamic programming.'
    },
    {
        'segment': 'Databases & SQL',
        'type': 'Core',
        'phase': 'Databases & SQL: Production Schema Design & Optimization',
        'duration': '1 Month',
        'topics': 'Introduction to DBMS & Keys, CRUD Operations (1 & 2), Joins, Aggregate Queries, Subqueries & Views, Indexing, Transactions & Isolation, Window Functions, Schema Design (1 & 2), Databases & SQL Contest.',
        'deliverable': 'Design ACID-compliant normalized relational database schemas with high-speed indexing & window queries.'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Specialisation',
        'phase': 'Foundations of Object-Oriented Design & Scalable Systems',
        'duration': '1 Month',
        'topics': 'Intro to LLD for Scalable & AI-Ready Systems, OOP Lab (Access Modifiers, Constructors, Inheritance, Polymorphism, Interfaces, Abstract Classes), Concurrency (Threads, Executors, Callables, Synchronization, Semaphores), Java Advanced Concepts (Generics, Collections, Streams, Lambdas, Exception Handling), Contest 1.',
        'deliverable': 'Multi-threaded thread-safe concurrent in-memory caching and messaging primitives.'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Specialisation',
        'phase': 'Design Principles & Patterns for Extensible Systems',
        'duration': '1 Month',
        'topics': 'SOLID Principles with AI integrations, Creational Patterns (Singleton, Builder, Prototype/Registry, Factory for Service Abstraction), Structural Patterns (Adapter, Facade, Decorator, Flyweight), Behavioural Patterns, UML Diagrams, Contest 2.',
        'deliverable': 'Architectural design blueprints conforming to strict SOLID principles and GoF design patterns.'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Specialisation',
        'phase': 'Applied Design & Machine Coding',
        'duration': '1 Month',
        'topics': 'Machine Coding Strategies under timed conditions, Design & Implement: TicTacToe (1 & 2), Parking Lot, BookMyShow (1, 2, 3), Splitwise (1 & 2), Machine Coding Evaluations.',
        'deliverable': 'Build complete, working, object-oriented machine-coded systems (Parking Lot, Splitwise, BookMyShow).'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Specialisation',
        'phase': 'AI-First Backend Capstone Project Primer',
        'duration': '1 Month',
        'topics': 'Intro to Backend Systems & AI-Augmented Development, Version Control & Git, Spring Framework & Building APIs, MVC & Microservices with AI Service Integration, 3rd Party APIs & LLM Services, Spring Data JPA, Automated Unit Testing, OAuth2 & JWT Security, AWS Cloud Deployment.',
        'deliverable': 'Live Spring Boot microservice deployed to AWS with AI service integration and automated authentication.'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Specialisation',
        'phase': 'AI-First Backend Capstone Advance & Build a Production-Ready AI System',
        'duration': '1.5 - 2.5 Months',
        'topics': 'RestTemplate Resilience, Mocking & Unit Tests, OAuth2, AWS (EBS, RDS, VPC, Route 53), Semantic Search, Stripe Payments & Reconciliation, Redis Caching & Kafka Queues, Spring Cloud, Docker, BookMyShow Chat Agent, Splitwise AI Receipt Processor.',
        'deliverable': 'Enterprise-grade microservices suite with Redis caching, Kafka streaming, and autonomous AI agents.'
    },
    {
        'segment': 'Fullstack Track',
        'type': 'Specialisation',
        'phase': 'Fullstack Web Platform, React & Backend Systems (Alternative Specialisation)',
        'duration': '4.5 Months',
        'topics': 'Web Platform Foundations (HTML5, Responsive CSS, Flexbox/Grid), JavaScript Runtime Systems (Execution Model, Closures, DOM, Async/Await, Weather App & Kanban Board Labs), React & Redux Product Architecture (IMDB Clone), Node.js, Express & MongoDB Production Systems.',
        'deliverable': 'Production MERN stack platform with real-time seat reservation engine and Redux state architecture.'
    },
    {
        'segment': 'System Design & Electives',
        'type': 'Elective',
        'phase': 'Distributed System Design & AI-Integrated Architectures',
        'duration': '1.5 Months',
        'topics': 'Load Balancing, Consistent Hashing, CDN & Caching at Scale, CAP/PACELC Theorem, Master-Slave Replication, SQL vs NoSQL, Database Sharding, Case Studies: Google Typeahead, Messaging Apps, Apache Kafka, ElasticSearch, S3/HDFS, Uber Nearest Neighbor, Rate Limiter, OTT Microservices.',
        'deliverable': 'Scalable distributed systems architectures engineered for 1M+ queries/sec with zero single points of failure.'
    },
    {
        'segment': 'Interview Prep & Electives',
        'type': 'Elective',
        'phase': 'Mastering LastMile Simulation & Emerging Tech Electives',
        'duration': '1.5 Weeks - 2 Months',
        'topics': 'DSA/LLD/HLD Interview Simulation under pressure, Data Engineering (PySpark, Hadoop, Hive, Spark Streaming, AWS), DSA Edge (Advanced Patterns), Product Management for Engineers, Gen AI for Software Engineers (RAG, Agents, Fine-Tuning, Quantization).',
        'deliverable': 'MAANG interview clearance readiness, high-throughput data pipelines, and production generative AI systems.'
    }
]

# 3. ADVANCED TRACK (Skips all Beginner Fundamentals & Intermediate DSA; System Design is CORE)
P1_ACADEMY_ADVANCED_MODULES = [
    {
        'segment': 'Agentic AI',
        'type': 'Core',
        'phase': 'AI & Agents: From Talking to AI to Building One',
        'duration': '1 Month',
        'topics': 'The runway to AI, GenAI World & LLM Landscape, Prompt Engineering Basics, Advanced Prompting & AI Safety Basics, LLM Built-in Power Tools, RAG Architectures, n8n Automation Workflows, What Is an AI Agent?, Building Agents with n8n, OpenClaw: Personal 24/7 AI Agent, Multi-Agent Systems, Debugging AI with Vibecoding Tools.',
        'deliverable': 'Deploy autonomous multi-agent developer workflows with n8n and build a personal 24/7 AI agent.'
    },
    {
        'segment': 'Advanced DSA',
        'type': 'Core',
        'phase': 'Advanced DSA: Foundations: Core Techniques & Optimization',
        'duration': '1 Month',
        'topics': 'Time Complexity Optimization, 1D & 2D Arrays Techniques, Bit Manipulation, Recursion, Maths: Modular Arithmetic & GCD, Hashing, Sorting (Count Sort, Merge Sort, Quick Sort & Comparators), Dual Camera Proctoring Contest 1.',
        'deliverable': 'Algorithmic problem-solving foundations, recursive tree modeling, and custom comparator sorting mastery.'
    },
    {
        'segment': 'Advanced DSA',
        'type': 'Core',
        'phase': 'Advanced DSA: Linear & Non-Linear Structures',
        'duration': '1 Month',
        'topics': 'Searching 1 (Binary Search on Array) & Searching 2 (Binary Search on Answer), Classes/Objects & Linked Lists, Stacks & Queues Architecture, Binary Trees Structure & Traversal, Binary Search Trees (BST), Contest 2.',
        'deliverable': 'Production implementation of custom non-linear data structures and BST operations.'
    },
    {
        'segment': 'Advanced DSA',
        'type': 'Core',
        'phase': 'Advanced DSA: Backtracking & Advanced Trees',
        'duration': '1 Month',
        'topics': 'Combinatorics & Primes, Two Pointers, Backtracking Masterclass, Morris Inorder Traversal, Lowest Common Ancestor (LCA), Advanced Hashing Internals, Contest 3.',
        'deliverable': 'Solve complex backtracking constraints, tree LCA, and Morris traversal with zero auxiliary space overhead.'
    },
    {
        'segment': 'Advanced DSA',
        'type': 'Core',
        'phase': 'Advanced DSA: DP, Heaps & Graphs - Crack It with AI Edge',
        'duration': '1 Month',
        'topics': 'Heaps & Heap Sort, Greedy Algorithms, Dynamic Programming (1D, 2D, Knapsack), Graphs 1 (DFS & Cycle Detection), Graphs 2 (BFS & MST), Graphs 3 (Dijkstra Algo & Topological Sort), Social Network Analyzer Capstone, Invoice Merger Capstone, Mandatory Skill Evaluation Test.',
        'deliverable': 'Production Capstones: Social Network Graph Analyzer & Invoice Merger; full graph traversal & dynamic programming.'
    },
    {
        'segment': 'Databases & SQL',
        'type': 'Core',
        'phase': 'Databases & SQL: Production Schema Design & Optimization',
        'duration': '1 Month',
        'topics': 'Introduction to DBMS & Keys, CRUD Operations (1 & 2), Joins, Aggregate Queries, Subqueries & Views, Indexing, Transactions & Isolation, Window Functions, Schema Design (1 & 2), SQL and Schema Design Contest.',
        'deliverable': 'Design ACID-compliant normalized relational database schemas with high-speed indexing & window queries.'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Specialisation',
        'phase': 'Foundations of Object-Oriented Design & Scalable Systems',
        'duration': '1 Month',
        'topics': 'Intro to LLD for Scalable & AI-Ready Systems, OOP Lab (Access Modifiers, Constructors, Inheritance, Polymorphism, Interfaces, Abstract Classes), Concurrency (Threads, Executors, Callables, Synchronization, Semaphores), Java Advanced Concepts (Generics, Collections, Streams, Lambdas, Exception Handling), Contest 1.',
        'deliverable': 'Multi-threaded thread-safe concurrent in-memory caching and messaging primitives.'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Specialisation',
        'phase': 'Design Principles & Patterns for Extensible Systems',
        'duration': '1 Month',
        'topics': 'SOLID Principles with AI integrations, Creational Patterns (Singleton, Builder, Prototype/Registry, Factory for Service Abstraction), Structural Patterns (Adapter, Facade, Decorator, Flyweight), Behavioural Patterns, UML Diagrams, Contest 2.',
        'deliverable': 'Architectural design blueprints conforming to strict SOLID principles and GoF design patterns.'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Specialisation',
        'phase': 'Applied Design & Machine Coding',
        'duration': '1 Month',
        'topics': 'Machine Coding Strategies under timed conditions, Design & Implement: TicTacToe (1 & 2), Parking Lot, BookMyShow (1, 2, 3), Splitwise (1 & 2), Low Level Design & Machine Coding Evaluations.',
        'deliverable': 'Build complete, working, object-oriented machine-coded systems (Parking Lot, Splitwise, BookMyShow).'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Specialisation',
        'phase': 'AI-First Backend Capstone Project Primer',
        'duration': '1 Month',
        'topics': 'Intro to Backend Systems & AI-Augmented Development, Version Control & Git, Spring Framework & Building APIs, MVC & Microservices with AI Service Integration, 3rd Party APIs & LLM Services, Spring Data JPA, Automated Unit Testing, OAuth2 & JWT Security, AWS Cloud Deployment.',
        'deliverable': 'Live Spring Boot microservice deployed to AWS with AI service integration and automated authentication.'
    },
    {
        'segment': 'Backend Specialisation',
        'type': 'Specialisation',
        'phase': 'AI-First Backend Capstone Advance & Build a Production-Ready AI System',
        'duration': '1.5 - 2.5 Months',
        'topics': 'RestTemplate Resilience, Mocking & Unit Tests, OAuth2, AWS (EBS, RDS, VPC, Route 53), Semantic Search, Stripe Payments & Reconciliation, Redis Caching & Kafka Queues, Spring Cloud, Docker, BookMyShow Chat Agent, Splitwise AI Receipt Processor.',
        'deliverable': 'Enterprise-grade microservices suite with Redis caching, Kafka streaming, and autonomous AI agents.'
    },
    {
        'segment': 'System Design',
        'type': 'Core',
        'phase': 'Distributed System Design & AI-Integrated Architectures',
        'duration': '1.5 Months',
        'topics': 'System Design Foundations & Modern Infrastructure, Load Balancing, Consistent Hashing & Traffic Routing at Scale, Caching Systems (CDN, Scaler Judge Leaderboards), CAP/PACELC Theorem, Master-Slave Replication, SQL vs NoSQL, Database Sharding, Case Studies: Google Typeahead, Messaging Apps (WhatsApp, FB Messenger), Apache Kafka, ElasticSearch, S3/HDFS, Uber Nearest Neighbor, Rate Limiter, OTT Microservices.',
        'deliverable': 'High-Level System Design architectures handling 1M+ RPS with high availability and zero single point of failure.'
    },
    {
        'segment': 'Interview Preparation',
        'type': 'Elective',
        'phase': 'Mastering LastMile - Interview Simulation',
        'duration': '1.5 Weeks',
        'topics': 'DSA Interview Simulation: Problem Solving & Thinking Under Pressure, LLD Interview Simulation: Structuring Scalable Solutions, HLD Interview Simulation: Designing Systems & Communicating Trade-offs.',
        'deliverable': 'Live simulated interview clearance benchmarked against MAANG hiring bars.'
    },
    {
        'segment': 'Electives',
        'type': 'Elective',
        'phase': 'Data Engineering, Gen AI for Software Engineers & Product Management',
        'duration': '1.5 - 2 Months',
        'topics': 'Data Engineering (PySpark, Hadoop, Hive, Spark Streaming, AWS), DSA Edge (Advanced Patterns, Tries, Bellman-Ford), Product Management for Engineers, Gen AI for Software Engineers (RAG, Agents, Fine-Tuning, Quantization).',
        'deliverable': 'High-throughput big data pipelines, fine-tuned domain models, and autonomous AI coding agents.'
    }
]

# ==============================================================================
# MODERN DATA SCIENCE & MACHINE LEARNING (DSML) - TRACK SPECIFIC CURRICULA
# ==============================================================================

# 1. BEGINNERS TRACK (14 - 21.5 Months - Foundations through Machine Learning & Agentic AI)
P2_DSML_BEGINNER_MODULES = [
    {
        'segment': 'Data Foundations & SQL',
        'type': 'Core',
        'phase': 'Advanced SQL & AI for Data Professionals',
        'duration': '2 Months',
        'topics': 'Data Foundations & SQL Intro, Schema Basics, Data Filtering, NULLs & Aggregation, GROUP BY Metrics, Applied SQL Labs (1 to 4), CASE WHEN, JOINs (INNER, LEFT, FULL OUTER, CROSS, SELF, NON-EQUI), Subqueries (Correlated & Non-Correlated, EXISTS), CTEs, Window Functions (ROW_NUMBER, Advanced Ranking, Navigation & Trends), Date/Time SQL, MySQL Setup, DDL/DML, Views, Indexing, Partitioning, Stored Procedures, Funnel Analytics & Cohort Retention.',
        'deliverable': 'Production SQL pipelines, cohort retention models, and sub-second analytical query optimization.'
    },
    {
        'segment': 'BI & Storytelling',
        'type': 'Core',
        'phase': 'Excel & Dashboarding with AI Storytelling',
        'duration': '1 Month',
        'topics': 'Excel (Structure, Formulas, Lookups, Pivot Tables, Mini Dashboard, Live Reporting Case), Tableau (Viz Fundamentals, KPIs, Filters, Calculations, Dashboard Labs, LOD Expressions, Table Calcs, Live Business Case 4: Dashboard Storytelling).',
        'deliverable': 'Interactive executive dashboards in Tableau and Excel with AI-powered KPI storytelling.'
    },
    {
        'segment': 'Programming for Data',
        'type': 'Core',
        'phase': 'Python Foundations + AI Coding Assistants',
        'duration': '1 Month',
        'topics': 'Python (Data Types, Variables, I/O, Control Flow, Loops, Functions, Lists, Strings, Data Structures, Debugging Masterclass), Pandas (Read, Filter, Select, Groupby KPIs, Merge, Cleaning, EDA & Data Quality Checks, Complete EDA).',
        'deliverable': 'Clean Python scripts, automated EDA pipelines, and robust data munging using Pandas.'
    },
    {
        'segment': 'Product Analytics',
        'type': 'Core',
        'phase': 'Data to Decisions: Product Analytics with AI',
        'duration': '1 Month',
        'topics': 'Metrics Foundations (DAU, MAU, Retention, Funnels), Event Tracking & Data Instrumentation, User Segmentation & Behavioral Analysis, Funnel Analysis, Cohort Analysis & Retention Deep Dive, Growth Metrics (Activation, Engagement, Retention), A/B Testing Fundamentals & Pitfalls, Revenue Metrics (AOV, LTV, CAC), Feature Adoption, AI for Product Analytics, Applied Product Lab.',
        'deliverable': 'Product analytics frameworks, user retention cohorts, and AI-driven growth hypothesis generation.'
    },
    {
        'segment': 'Analytics Automation',
        'type': 'Core',
        'phase': 'Generative AI for Data Analytics & Automation',
        'duration': '1 Month',
        'topics': 'GenAI & LLMs for Analysts, Prompt Engineering for Data (SQL, Python, Insights), AI for SQL Query Generation & Debugging, Python/Pandas Automation, AI for Data Cleaning & EDA, Dashboard Insights & Storytelling, AI-Assisted Reports, Automating Repetitive Analysis, Evaluating AI Outputs (Hallucination, Bias), OpenAI APIs for Data Workflows, Mini AI Tools, Applied GenAI Lab.',
        'deliverable': 'Autonomous analyst workflows, automated report generation, and custom OpenAI-powered data tools.'
    },
    {
        'segment': 'Career Readiness',
        'type': 'Core',
        'phase': 'Interview Readiness: Technical & Product Cases',
        'duration': '1 Month',
        'topics': 'SQL Pattern Recognition & Case-Based Problem Solving (JOINs, Window Functions, CTEs), Python & Pandas Technical Interview Prep, Product Case Interviews (Metrics & Business Thinking), Estimation & Guesstimates, Resume Building (Projects, Impact, Storytelling), LinkedIn & Portfolio Optimization.',
        'deliverable': 'Analyst portfolio, case study defense, and technical interview clearance for Tier-1 data teams.'
    },
    {
        'segment': 'Advanced Data Engineering',
        'type': 'Core',
        'phase': 'Advanced Analytics with Python, Pandas & AI Workflows',
        'duration': '1 Month',
        'topics': 'Python Refresher, Data Manipulation & Chaining, Groupby Transformations, Multi-Table Data Handling, Handling Large Datasets, Data Cleaning at Scale, NumPy Foundations & Advanced NumPy for Analytics, Data Visualization & Feature Engineering, Automation Scripts & Scheduling, AI-Assisted Analysis & Code Generation, End-to-End AI Data Solutions.',
        'deliverable': 'Scalable data manipulation pipelines processing massive multi-table datasets with automated feature engineering.'
    },
    {
        'segment': 'Applied Statistics',
        'type': 'Core',
        'phase': 'Statistics, Experimentation & AI for Data-Driven Decisions',
        'duration': '1 Month',
        'topics': 'Probability Foundations, Distributions (Normal, Binomial), Sampling Techniques & Bias, Central Limit Theorem (Intuition + Applications), Hypothesis Testing Fundamentals, p-values, Confidence Intervals & Errors, A/B Testing (Design, Setup, Analysis & Interpretation), Experimentation Pitfalls (Bias, Peeking, Simpson\'s Paradox), Metric Design, AI-Assisted Statistical Interpretation & Validation, Applied Experiment Lab.',
        'deliverable': 'Rigorous statistical A/B testing framework evaluated by product tech leaders.'
    },
    {
        'segment': 'Product Analytics',
        'type': 'Core',
        'phase': 'Advanced Product Analytics & Strategy',
        'duration': '1 Month',
        'topics': 'Advanced Funnel Analysis (Multi-step, Multi-channel), Retention Models & Cohort Deep Dive, Customer Lifetime Value (LTV) Modeling, Customer Acquisition Cost (CAC) & Payback, Growth Loops & Product-Led Growth, Segmentation Strategies (Behavioral & Value-based), Churn Analysis & Retention Strategies, Predictive Analytics for Product, Recommendation Systems (Conceptual), Decision Frameworks, AI for Product Strategy, Applied Product Capstone.',
        'deliverable': 'End-to-end product strategy and predictive customer retention model capstone.'
    },
    {
        'segment': 'Domain Analytics',
        'type': 'Elective',
        'phase': 'Domain Analytics (FinTech, E-Commerce, HealthTech)',
        'duration': '1 Month',
        'topics': 'E-commerce Analytics & Basket Analysis, FinTech Risk & Fraud Modeling, HealthTech Analytics, SaaS Growth Metrics, Custom Domain Case Studies.',
        'deliverable': 'Specialized industry capstone solving real enterprise domain problem statements.'
    },
    {
        'segment': 'Cloud Analytics',
        'type': 'Elective',
        'phase': 'Cloud & Data Analytics on AWS',
        'duration': '1 Month',
        'topics': 'Modern Cloud Data Stack, AWS Fundamentals (S3, IAM), S3 Data Lakes, Querying Data with Amazon Athena, Data Warehousing with Amazon Redshift, ETL with AWS Glue, End-to-End Data Pipelines, Connecting Tableau to Cloud Data Sources, Performance & Cost Optimization, Intro to Databricks & Lakehouse Concept, Applied Cloud Lab.',
        'deliverable': 'Production cloud data lakehouse on AWS with Athena, Redshift, and automated Glue ETL.'
    },
    {
        'segment': 'Applied AI',
        'type': 'Core',
        'phase': 'AI For Everyone & Autonomous Workflows',
        'duration': '2 Months',
        'topics': 'Comparative Framework for AI Tools, Model Selection, AI Failure Modes & Mitigation, Voice-Driven Analytical Workflows, No-Code Process Automation for Data, Org Knowledge Bases Integration, Reusable Prompt Libraries, Project Task Decomposition, Three-Tier Workflow Mapping, No-Code Prototyping, Autonomous AI Boundaries, Multi-Step AI Pipelines, Applied Agent Dev (Data Monitoring Workflow), AI-Assisted Presentations & Communicating AI Work Responsibly.',
        'deliverable': 'Autonomous data-monitoring AI agents and no-code analytical tools deployed across enterprise workflows.'
    },
    {
        'segment': 'Mathematical Foundations',
        'type': 'Core',
        'phase': 'Mathematical Foundations for AI',
        'duration': '1 Month',
        'topics': 'Linear Algebra in ML (Dot products, hyperplanes, halfspaces, distance, loss minimization in classification), Calculus & Optimization (Gradient descent in action, constrained optimization, Principal Component Analysis PCA).',
        'deliverable': 'Mathematical vector foundations and custom gradient descent optimization engine from scratch.'
    },
    {
        'segment': 'Machine Learning',
        'type': 'Core',
        'phase': 'Machine Learning with AI Workflows',
        'duration': '1 Month',
        'topics': 'Intro to ML, Linear Regression (1 to 4), Polynomial Regression, Bias-Variance Tradeoff, Regularization (L1/L2), Cross-Validation, Logistic Regression (1 & 2), Classification Metrics (Confusion Matrix, ROC-AUC, Imbalanced Data).',
        'deliverable': 'Calibrated predictive regression and classification pipelines handling imbalanced enterprise data.'
    },
    {
        'segment': 'Machine Learning',
        'type': 'Elective',
        'phase': 'Supervised Machine Learning with AI',
        'duration': '1 Month',
        'topics': 'k-Nearest Neighbors (1 & 2), Decision Trees (1 & 2), Bagging & Random Forest, Boosting (AdaBoost, Gradient Boosting, XGBoost), Ensemble Techniques, Naive Bayes (1 & 2), Support Vector Machines (SVM 1 & 2), Supervised ML Wrap-up.',
        'deliverable': 'Tuned ensemble models (XGBoost, Random Forest) solving complex classification challenges.'
    },
    {
        'segment': 'Machine Learning',
        'type': 'Elective',
        'phase': 'Un-supervised Machine Learning with AI',
        'duration': '1 Month',
        'topics': 'Dimensionality Reduction (PCA, t-SNE, UMAP), Clustering (K-Means, K-Means++, Gaussian Mixture Models GMM, Hierarchical Clustering, DBSCAN), Anomaly Detection, End-to-End Business Cases (1 & 2).',
        'deliverable': 'High-dimensional customer segmentation and anomaly detection engines.'
    },
    {
        'segment': 'Forecasting & Recommenders',
        'type': 'Elective',
        'phase': 'Time Series and Recommender Systems with AI Workflows',
        'duration': '1 Month',
        'topics': 'Time Series Forecasting (ARIMA, SARIMA, Prophet), Trend & Seasonality Decomposition, Recommender Systems (Collaborative Filtering, Matrix Factorization, Content-Based, Hybrid Engines), End-to-end Practical Session.',
        'deliverable': 'Scalable multi-modal recommendation engine and automated time-series demand forecasting system.'
    },
    {
        'segment': 'MLOps & Platform',
        'type': 'Elective',
        'phase': 'MLOps & AI Deployment',
        'duration': '1 Month',
        'topics': 'Git & GitHub for MLOps, Building Streamlit Tools (Cars24 case), Web APIs using Flask/FastAPI, Containerization with Docker & DockerHub, Deploying APIs on AWS ECS, CI/CD with GitHub Actions, Experiment Tracking with MLflow, ML System Design (1 & 2), AWS SageMaker Pipelines, Large-scale processing with Apache Spark.',
        'deliverable': 'End-to-end production CI/CD MLOps pipeline on AWS ECS with Docker, MLflow, and SageMaker.'
    },
    {
        'segment': 'Deep Learning',
        'type': 'Elective',
        'phase': 'Deep Learning & Neural Networks',
        'duration': '1 Month',
        'topics': 'Neural Networks Intro, Forward & Backpropagation, N-Layer Neural Networks, Backprop Mathematics, TensorFlow & Keras (1 & 2), Optimizers (Adam, RMSprop), Hyperparameter Tuning, Autoencoders, MLP Design & Debugging, Model Interpretability (LIME).',
        'deliverable': 'Multi-layer perceptron neural network architectures with custom optimizers and explainability frameworks.'
    },
    {
        'segment': 'Computer Vision',
        'type': 'Elective',
        'phase': 'AI for Computer Vision',
        'duration': '1 Month',
        'topics': 'Computer Vision Intro (CNNs), Addressing Overfitting, CNN under the hood, Transfer Learning, Image Similarity & Embeddings, CNN for Medical Diagnosis, Object Localization & Detection (YOLO), Object Segmentation, Siamese Networks, Generative Models & GANs Intro.',
        'deliverable': 'Real-time object detection and visual feature extraction pipeline using Transfer Learning.'
    },
    {
        'segment': 'Natural Language Processing',
        'type': 'Elective',
        'phase': 'AI for Natural Language Processing',
        'duration': '1 Month',
        'topics': 'NLP Foundations, Text Representation, Word Embeddings (Word2Vec), Language Modeling, Topic Modeling, RNNs, LSTMs, Named Entity Recognition (NER), Attention Mechanisms, Transformer Architecture, BERT.',
        'deliverable': 'Production text intelligence pipeline with named entity extraction and transformer embeddings.'
    },
    {
        'segment': 'Agentic AI',
        'type': 'Elective',
        'phase': 'AI Engineering and Agentic AI',
        'duration': '1.5 Months',
        'topics': 'AI Engineering Intro, Modern Text & Image Model Architectures, Text Generation APIs (OpenAI), Eval Pipelines & Observability, Prompt Engineering & Security, RAG & Embeddings Deep Dive, Multimodal & Tabular RAG, Autonomous Agents (Foundations, Planning, Frameworks & Protocols - LangGraph/CrewAI), Fine-Tuning Models, Scaling AI Apps, Quantization, Inference Optimization.',
        'deliverable': 'Enterprise Autonomous Multi-Agent reasoning system and production RAG pipeline.'
    }
]

# 2. INTERMEDIATE TRACK (11.5 Months - Core ML, MLOps, Deep Learning & Agentic AI)
P2_DSML_INTERMEDIATE_MODULES = [
    {
        'segment': 'Advanced Data Engineering',
        'type': 'Core',
        'phase': 'Advanced Analytics with Python, Pandas & AI Workflows',
        'duration': '1 Month',
        'topics': 'Python Refresher, Data Manipulation & Chaining, Groupby Transformations, Multi-Table Data Handling, Handling Large Datasets, Data Cleaning at Scale, NumPy Foundations & Advanced NumPy for Analytics, Data Visualization & Feature Engineering, Automation Scripts & Scheduling, AI-Assisted Analysis & Code Generation, End-to-End AI Data Solutions.',
        'deliverable': 'Scalable data manipulation pipelines processing massive multi-table datasets with automated feature engineering.'
    },
    {
        'segment': 'Applied Statistics',
        'type': 'Core',
        'phase': 'Statistics, Experimentation & AI for Data-Driven Decisions',
        'duration': '1 Month',
        'topics': 'Probability Foundations, Distributions (Normal, Binomial), Sampling Techniques & Bias, Central Limit Theorem (Intuition + Applications), Hypothesis Testing Fundamentals, p-values, Confidence Intervals & Errors, A/B Testing (Design, Setup, Analysis & Interpretation), Experimentation Pitfalls (Bias, Peeking, Simpson\'s Paradox), Metric Design, AI-Assisted Statistical Interpretation & Validation, Applied Experiment Lab.',
        'deliverable': 'Rigorous statistical A/B testing framework evaluated by product tech leaders.'
    },
    {
        'segment': 'Product Analytics',
        'type': 'Core',
        'phase': 'Advanced Product Analytics',
        'duration': '1 Month',
        'topics': 'Advanced Funnel Analysis (Multi-step, Multi-channel), Retention Models & Cohort Deep Dive, Customer Lifetime Value (LTV) Modeling, Customer Acquisition Cost (CAC) & Payback, Growth Loops & Product-Led Growth, Segmentation Strategies (Behavioral & Value-based), Churn Analysis & Retention Strategies, Predictive Analytics for Product, Recommendation Systems (Conceptual), Decision Frameworks, AI for Product Strategy, Applied Product Capstone.',
        'deliverable': 'End-to-end product strategy and predictive customer retention model capstone.'
    },
    {
        'segment': 'Mathematical Foundations',
        'type': 'Core',
        'phase': 'Mathematical Foundations for AI',
        'duration': '1 Month',
        'topics': 'Linear Algebra in ML (Dot products, hyperplanes, halfspaces, distance, loss minimization in classification), Calculus & Optimization (Gradient descent in action, constrained optimization, Principal Component Analysis PCA).',
        'deliverable': 'Mathematical vector foundations and custom gradient descent optimization engine from scratch.'
    },
    {
        'segment': 'Machine Learning',
        'type': 'Core',
        'phase': 'Machine Learning with AI Workflows',
        'duration': '1 Month',
        'topics': 'Intro to ML, Linear Regression (1 to 4), Polynomial Regression, Bias-Variance Tradeoff, Regularization (L1/L2), Cross-Validation, Logistic Regression (1 & 2), Classification Metrics (Confusion Matrix, ROC-AUC, Imbalanced Data).',
        'deliverable': 'Calibrated predictive regression and classification pipelines handling imbalanced enterprise data.'
    },
    {
        'segment': 'Supervised Learning',
        'type': 'Core',
        'phase': 'Supervised Machine Learning with AI',
        'duration': '1 Month',
        'topics': 'k-Nearest Neighbors (1 & 2), Decision Trees (1 & 2), Bagging & Random Forest, Boosting (AdaBoost, Gradient Boosting, XGBoost), Ensemble Techniques, Naive Bayes (1 & 2), Support Vector Machines (SVM 1 & 2), Supervised ML Wrap-up.',
        'deliverable': 'Tuned ensemble models (XGBoost, Random Forest) solving complex classification challenges.'
    },
    {
        'segment': 'Unsupervised Learning',
        'type': 'Core',
        'phase': 'Un-supervised Machine Learning with AI',
        'duration': '1 Month',
        'topics': 'Dimensionality Reduction (PCA, t-SNE, UMAP), Clustering (K-Means, K-Means++, Gaussian Mixture Models GMM, Hierarchical Clustering, DBSCAN), Anomaly Detection, End-to-End Business Cases (1 & 2).',
        'deliverable': 'High-dimensional customer segmentation and anomaly detection engines.'
    },
    {
        'segment': 'Forecasting & Recommenders',
        'type': 'Core',
        'phase': 'Time Series and Recommender Systems with AI Workflows',
        'duration': '1 Month',
        'topics': 'Time Series Forecasting (ARIMA, SARIMA, Prophet), Trend & Seasonality Decomposition, Recommender Systems (Collaborative Filtering, Matrix Factorization, Content-Based, Hybrid Engines), End-to-end Practical Session.',
        'deliverable': 'Scalable multi-modal recommendation engine and automated time-series demand forecasting system.'
    },
    {
        'segment': 'MLOps & Platform',
        'type': 'Core',
        'phase': 'MLOps & AI Deployment',
        'duration': '1 Month',
        'topics': 'Git & GitHub for MLOps, Building Streamlit Tools (Cars24 case), Web APIs using Flask/FastAPI, Containerization with Docker & DockerHub, Deploying APIs on AWS ECS, CI/CD with GitHub Actions, Experiment Tracking with MLflow, ML System Design (1 & 2), AWS SageMaker Pipelines, Large-scale processing with Apache Spark.',
        'deliverable': 'End-to-end production CI/CD MLOps pipeline on AWS ECS with Docker, MLflow, and SageMaker.'
    },
    {
        'segment': 'Deep Learning',
        'type': 'Core',
        'phase': 'Deep Learning & Neural Networks',
        'duration': '1 Month',
        'topics': 'Neural Networks Intro, Forward & Backpropagation, N-Layer Neural Networks, Backprop Mathematics, TensorFlow & Keras (1 & 2), Optimizers (Adam, RMSprop), Hyperparameter Tuning, Autoencoders, MLP Design & Debugging, Model Interpretability (LIME).',
        'deliverable': 'Multi-layer perceptron neural network architectures with custom optimizers and explainability frameworks.'
    },
    {
        'segment': 'Agentic AI',
        'type': 'Core',
        'phase': 'AI Engineering and Agentic AI',
        'duration': '1.5 Months',
        'topics': 'Introduction to AI Engineering, Refresher on Modern Text & Image Model Architectures, Text Generation APIs (OpenAI API), Eval Pipelines & Observability, Prompt Engineering & Security, Retrieval-Augmented Generation (RAG) & Embeddings Deep Dive, Multimodal & Tabular RAG, Autonomous Agents (Foundations, Planning, Frameworks & Protocols), Fine-Tuning Existing Models, Modalities (Audio, Image, Video), Scaling AI Applications, Model Quantization, Advanced Fine-Tuning, Dataset Engineering & Inference Optimization.',
        'deliverable': 'Production-grade enterprise Autonomous Agent systems, optimized fine-tuned LLMs, and high-performance RAG architectures.'
    }
]

# ==============================================================================
# AI FORWARD DEPLOYED ENGINEER (FDE) - COMPREHENSIVE CURRICULUM & DEEP DIVE
# ==============================================================================

P3_FDE_MODULES = [
    {
        'segment': 'Enterprise Data & Role Playbook',
        'type': 'Core',
        'phase': 'The FDE Launchpad — Role, SQL & the Legacy Data Problem',
        'duration': '1.25 Months',
        'topics': 'Your Playbook for Every Client Room, The Artifact Toolkit That Runs Every Engagement, Meet the Schema - From Entities to Queries, Reporting Views That Run the Dashboard, Find the Bottleneck, Fix the Query, No Half-Measures - Atomic Updates That Don\'t Corrupt, Designing a Schema the Client Won\'t Outgrow, Building Meridian\'s Full Data Model, Lock It Down - PII, Encryption & Audit Trails, Reaching Across the Firewall - Legacy Data Access, Picking the Right Engine for the Job, Quick Diagnostics Before the Pipeline Exists, Designing the Pipeline - ETL Thinking, Explaining Your Schema to the VP Who Signs Off, Turning Query Results into Client-Ready Insight.',
        'deliverable': 'Production enterprise data model (Meridian Data Architecture), legacy data access bridge, and client-ready analytical views with audit trails.'
    },
    {
        'segment': 'Data Ingestion & Concurrency',
        'type': 'Core',
        'phase': 'The Ingestion Pipeline — Production Python',
        'duration': '1.25 Months',
        'topics': 'Your Workbench - Python Toolchain Done Right, Stream It, Don\'t Load It, Reusable Building Blocks - Decorators & Context Managers, Modeling the Real World in Code, Make It Fast - Concurrency & Async, When the Data Fights Back - Error Handling & Resilience, Validate Everything, Log Everything, Prove It Works - Testing & CI, Code That Survives the Next Engineer, PySpark - When Python Meets Big Data, Pipeline Day - Full PySpark Ingestion Build, Under Pressure - Timed Python Build, PR Reviews That Build Trust, Write the Doc They\'ll Actually Read.',
        'deliverable': 'Resilient, high-throughput asynchronous PySpark ingestion pipeline processing enterprise streaming and batch feeds.'
    },
    {
        'segment': 'Enterprise Backend & APIs',
        'type': 'Core',
        'phase': 'The Platform Backend — Orders, Payments & Real-Time',
        'duration': '1.75 Months',
        'topics': 'Your First Production API, Routing the First Request, Making FastAPI Do the Heavy Lifting, Consuming APIs Like a Professional, Who Gets In - Auth Done Right with OAuth2 & JWT, Locking Doors by Role - RBAC, OIDC & Multi-Tenant Auth, The Order Lifecycle - State Machines in Production, Money and Messages - Payments & Notifications, The Contract Between Backend & Frontend, Break the Contract, Break the Build, Push, Don\'t Poll - WebSockets & Server-Sent Events, Queues, Cache, Invalidate - Redis & Message Patterns, Observability & Tracing, Beyond Rows - JSONB, Full-Text Search & Vector Storage, Warehouse Layer - dbt, DuckDB & Dimensional Modeling, Orchestrating the Nightly Pipeline, Kafka Fundamentals, Pipeline Under Fire - Timed Debug Challenge, Running the Room - API Reviews & Incident Updates.',
        'deliverable': 'Production FastAPI enterprise service with multi-tenant RBAC, Kafka event bus, Redis caching, and real-time WebSockets.'
    },
    {
        'segment': 'Client-Facing Systems & UI',
        'type': 'Core',
        'phase': 'The Ops Dashboard — React, TypeScript & Real-Time UI',
        'duration': '1 Month',
        'topics': 'How the Web Works: From DOM to Dashboard, Async, Typed and Connected: Talking to the Backend, Thinking in Components: Building the Dashboard One Boundary at a Time, Forms That Don\'t Frustrate: Validation, Control and Reuse, Wiring the Dashboard Live: APIs, Caching and Server State, KPIs, Tables and Filters: The Dashboard Takes Shape, Defending the Architecture: React Decisions and Next.js Awareness, Gating the Dashboard: Authentication, Roles and Protected Routes, Real-Time and AI-Ready Interfaces, Fast, Reliable and Ready: Testing and Performance, Defending the Solution to Leadership, The Handover Moment: Walking the Ops Team Through Their Dashboard.',
        'deliverable': 'Modern enterprise React/Next.js client operations dashboard with live KPI state management and role-gated UI routes.'
    },
    {
        'segment': 'Enterprise RAG & Evaluation',
        'type': 'Core',
        'phase': 'The New Ask — Production RAG for Customer Support',
        'duration': '1 Month',
        'topics': 'The AI Landscape - Picking Your Weapons, Your First System Prompt - And Why It\'ll Break, Choosing How to Serve - APIs, Context & Parameters, Prompts as Code - Versioning & Regression Testing, Building the Knowledge Pipeline - RAG End to End, Does It Actually Find the Right Answer?, Does It Tell the Truth? - Generation Eval & RAGAS, Guardrails That Actually Work - PII Leak Prevention, Red Team Your Own Copilot, Spend Less, Answer Faster, Ship It - Timed RAG Build, Explaining AI Risk Without Scaring the Room, Making Eval Numbers Mean Something to the Board.',
        'deliverable': 'Production RAG customer copilot evaluated with RAGAS, protected by PII guardrails, and optimized for latency/token spend.'
    },
    {
        'segment': 'Autonomous Agents & Protocols',
        'type': 'Core',
        'phase': 'From Answering to Acting — Agents & Enterprise Integration',
        'duration': '1.25 Months',
        'topics': 'From Chatbot to Coworker, Giving the Agent Real Tools, Orchestrating Agent Intelligence with LangGraph, Production Agent Patterns, When the Agent Breaks, MCP - The Universal Tool Protocol, The Agent Team - Multi-Agent & Human-in-the-Loop, Mapping the Client\'s System Landscape, Data Integration with Legacy Enterprise Systems, Wiring It Together - API Connectors & Webhooks, When the Integration Breaks, Ship Day - The Full Agentic Copilot Goes Live, Red-Team War Room, Explaining What the Agent Will and Won\'t Do Alone, Getting the Client\'s IT Team on Your Side.',
        'deliverable': 'LangGraph multi-agent autonomous system integrated via Model Context Protocol (MCP) and enterprise webhooks.'
    },
    {
        'segment': 'Distributed Systems & Scale',
        'type': 'Core',
        'phase': 'The Scale Question — System Design for Black Friday',
        'duration': '1.25 Months',
        'topics': 'The System Design Playbook, Spreading the Load, Cache Everything, Consistency vs Availability, When One Database Isn\'t Enough, Shard It and Build It, When Your Table Hits 10TB, The Event Backbone - Kafka at Scale, Search That Scales, Rate Limiting & Unique IDs, Monolith or Microservices, Distributed Transactions - Saga vs 2PC, Whiteboarding With the Client\'s Architects, System Design Under Pressure.',
        'deliverable': 'Resilient, multi-region distributed system architecture capable of surviving 10x traffic spikes with zero data loss.'
    },
    {
        'segment': 'AI Infrastructure & Architecture',
        'type': 'Core',
        'phase': 'Scaling the AI Layer — Enterprise AI Architecture',
        'duration': '1 Month',
        'topics': 'Serving AI at Scale, One Gateway, Many Models, GPU Math - Capacity Planning, When to Fine-Tune - And When Not To, Embedding Pipelines at Scale, Vector Search at Billion Scale, Evals as Infrastructure, Tracking Experiments - MLflow & Model Registries, Ship Without Breaking - Canary Rollouts for AI, Is the AI Drifting?, Defend Your AI Architecture, Selling the AI Stack to the Board.',
        'deliverable': 'Billion-scale vector search and unified multi-model LLM gateway with canary deployment infrastructure.'
    },
    {
        'segment': 'Systems & Linux Infrastructure',
        'type': 'Core',
        'phase': 'Prepping the Ground — Linux, Networking & Shell',
        'duration': '1 Month',
        'topics': 'Your First Server, Who Gets Access, What\'s Running and Why, Finding the Needle, How Packets Flow, Locking Down the Network, TCP vs. UDP: Below the Surface, Automate the Boring Stuff, Scripts That Keep the Lights On, The Log Parser, Write the Runbook the 3AM Engineer Will Thank You For.',
        'deliverable': 'Hardened Linux operating environment, automated Bash maintenance runbooks, and locked-down network routing.'
    },
    {
        'segment': 'Containers & Orchestration',
        'type': 'Core',
        'phase': 'Containerizing Meridian — Docker & Kubernetes',
        'duration': '1.25 Months',
        'topics': 'Containers 101, Slim, Fast and Secure Images in Production, Containers Talking to Each Other, Hardening Containers, Why You Need an Orchestrator, Deploy It, Wiring Services Together, Scale/Update Under Pressure, Lock It Down, Production K8s, The Pod Won\'t Start, Deploying AI Models on a Cluster, GitOps - Declarative Deployments with ArgoCD, Do We Really Need Kubernetes?, Coordinating the Rollout.',
        'deliverable': 'Production Kubernetes deployment with ArgoCD declarative GitOps, zero-downtime rollouts, and secure container images.'
    },
    {
        'segment': 'Cloud & Infrastructure as Code',
        'type': 'Elective',
        'phase': 'Going Live — AWS Production Deployment with Terraform',
        'duration': '2.25 Months',
        'topics': 'Designing Cloud Network, Compute on AWS, Load Balancing Across AZs, Object Storage, SQL & NoSQL in Cloud, Caching, Locking Down Cloud, Breach Drill, Kubernetes in Cloud (I, II, III), Securing Meridian\'s Cluster, Data & Application, Cert Manager & Route 53 (SSL + DNS), AWS Capstone Kickoff, EKS Capstone (Parts 1 & 2), Cloud Rosetta Stone (AWS ↔ GCP ↔ Azure), Boardroom Cloud Talk, War-Room 101, IaC - Terraform Fundamentals & In Action, CI Pipelines, Deploying Docker Image to EKS.',
        'deliverable': '1-Click Terraform IaC cloud infrastructure on AWS EKS with multi-AZ load balancing, SSL, and automated CI pipelines.'
    },
    {
        'segment': 'SRE & Disaster Recovery',
        'type': 'Elective',
        'phase': 'Making It Bulletproof — Reliability, HA & Disaster Recovery',
        'duration': '1 Month',
        'topics': 'SRE - When 99.9% Isn\'t Enough, Surviving Region Failure - HA Architecture, The DR Plan Nobody Tests (Until It\'s Too Late), Sharding in Production, Breaking to Ensure It Doesn\'t Break (Chaos Engineering), CRDs, Operators & Admission Webhooks in Kubernetes, Advanced AWS Networking, NoSQL & Caching on AWS, Load Testing at Scale - Proving It Before Black Friday, The Reliability Check, Selling Reliability to the CFO.',
        'deliverable': 'Active-active multi-region Disaster Recovery plan, Kubernetes Operators, and Chaos Engineering verified reliability suite.'
    },
    {
        'segment': 'Security & Governance',
        'type': 'Elective',
        'phase': 'Enterprise Sign-Off — Security Hardening & Incident Response',
        'duration': '0.75 Months',
        'topics': 'Threat Modeling - Where Will They Attack?, OWASP Top 10 - Hands-On Exploitation & Defence, Securing the AI Layer, Secrets, Keys & Certificates Lifecycle, Compliance Frameworks - SOC2, GDPR & What FDEs Actually Do, Penetration Testing Your Own Platform, The Incident Response Playbook, Incident Simulation - Full Red Team Exercise, The Security Briefing the Board Actually Needs.',
        'deliverable': 'SOC2/GDPR compliance posture, automated threat defense, secrets rotation vault, and board-ready security clearance.'
    },
    {
        'segment': 'Client Simulation Capstone',
        'type': 'Elective',
        'phase': 'Capstone & Hiring Readiness — New Client, Full Simulation',
        'duration': '1 Month',
        'topics': 'New Brief, Day One - The Capstone Kickoff, Build Sprint 1 (Data & Backend), Build Sprint 2 (Frontend & AI Feature), Red Team Day - Classmates Break Your Build, Portfolio Day - Packaging Meridian for Interviews, System Design Interview Prep, Behavioral & FDE Interview Prep, Capstone Demo Day - Graduation.',
        'deliverable': 'End-to-end client engagement simulation (Meridian Platform) presented and defended before enterprise engineering directors.'
    }
]



# ==============================================================================
# PROGRAM 4: AI & MACHINE LEARNING WITH AGENTIC AI - OFFICIAL TRACK CURRICULA
# ==============================================================================

# Core shared modules
P4_AIML_DATA_FOUNDATIONS = {
    'segment': 'Data Foundations',
    'type': 'Core',
    'phase': 'Data Foundations',
    'duration': '1 Month',
    'topics': 'Numpy / Pandas, Data frames, EDA, Data Plotting and visualisation basics, Probability Foundations.',
    'deliverable': 'Comprehensive exploratory data analysis (EDA) pipeline with automated summary statistics, data plotting, and probabilistic inference.'
}

P4_AIML_SUPERVISED = {
    'segment': 'ML Coding (Applied AI-ML)',
    'type': 'Core',
    'phase': 'Supervised Learning',
    'duration': '1.5 Months',
    'topics': 'Linear Regression, regression metrics and Sklearn pipelines, Logistic Regression, Classification Metrics, KNN, Decision Trees, Bagging & Boosting, Naive Bayes.',
    'deliverable': 'Production Scikit-Learn machine learning pipelines with cross-validated hyperparameter tuning and model performance evaluation.'
}

P4_AIML_UNSUPERVISED_TS_REC = {
    'segment': 'ML Coding (Applied AI-ML)',
    'type': 'Core',
    'phase': 'Unsupervised Learning, Time series & Recommender Systems',
    'duration': '1.5 Months',
    'topics': 'Clustering, Anomaly Detection, GMM, Dimensionality Reduction, Time series pre-processing and decomposition, Time series analysis, Collaborative filtering & ARM, Content based filtering.',
    'deliverable': 'Hybrid recommender engine and time-series demand forecasting system with automated anomaly detection.'
}

P4_AIML_NEURAL_NETWORKS = {
    'segment': 'ML Coding (Applied AI-ML)',
    'type': 'Core',
    'phase': 'Neural Networks',
    'duration': '1 Month',
    'topics': 'Neural Networks, Optimizers, Loss function, activation functions, weight initialization, regularization.',
    'deliverable': 'Custom deep neural network built and optimized from first principles with custom backpropagation and adaptive learning rate schedulers.'
}

P4_AIML_CV_NLP = {
    'segment': 'ML Coding (Applied AI-ML)',
    'type': 'Core',
    'phase': 'Computer Vision and Natural Language Processing',
    'duration': '1 Month',
    'topics': 'OpenCV, Applied Deep Learning (CNNs, LSTM, GRU, Autoencoders, etc), Transfer Learning, Advance Computer Vision - Image gen, Face detection / recognition, segmentation, Text Pre-Processing (NLTK/spaCy), topic modelling, Sentiment Analysis, LSTM, RNN, Attention, Advanced NLP - Transformers / GPT.',
    'deliverable': 'Dual-modal vision and language solution combining computer vision segmentation with Transformer/GPT text classification.'
}

P4_AIML_MLOPS = {
    'segment': 'ML & Gen AI Engineering',
    'type': 'Core',
    'phase': 'MLOps',
    'duration': '1.5 Months',
    'topics': 'ML lifecycle, CI/CD pipelines, Feature Stores for ML, Serving ML Models, ML Monitoring, Experiment tracking, MLflow, Docker, Optuna, AWS SageMaker.',
    'deliverable': 'Automated end-to-end MLOps deployment pipeline on AWS SageMaker with MLflow experiment tracking, Dockerized containers, and live drift monitoring.'
}

P4_AIML_SYSTEM_DESIGN = {
    'segment': 'ML & Gen AI Engineering',
    'type': 'Core',
    'phase': 'System Design',
    'duration': '1 Month',
    'topics': 'ML System Design fundamentals, Microservices, Design Patterns, Scalability and Cost.',
    'deliverable': 'Enterprise ML system design blueprint addressing microservices partitioning, caching layers, distributed throughput, and infrastructure cost optimization.'
}

P4_AIML_FOUNDATIONS_RAG = {
    'segment': 'ML & Gen AI Engineering',
    'type': 'Core',
    'phase': 'Foundations of AI Engineering & RAG Systems',
    'duration': '1.5 Months',
    'topics': 'Prompt Engineering, Jailbreaks, and Guardrails, RAG Systems, Vector Databases, and Embeddings.',
    'deliverable': 'Enterprise Retrieval-Augmented Generation (RAG) system with semantic chunking, vector database indexation, and safety guardrails.'
}

P4_AIML_AGENTIC_PATTERNS = {
    'segment': 'ML & Gen AI Engineering',
    'type': 'Core',
    'phase': 'Agentic Design Patterns & Multi-Agent Orchestration',
    'duration': '1.5 Months',
    'topics': 'LangChain, LangGraph, Memory Systems (Short-term, Long-term, Episodic).',
    'deliverable': 'Autonomous multi-agent orchestration architecture in LangGraph equipped with episodic memory, cyclical state machines, and dynamic tool calling.'
}

P4_AIML_ADVANCED_COGNITIVE = {
    'segment': 'ML & Gen AI Engineering',
    'type': 'Core',
    'phase': 'Advanced Cognitive Architectures & Multimodal Intelligence',
    'duration': '1 Month',
    'topics': 'Agentic RAG, GraphRAG, Multimodal AI (Vision with GPT-4V/LLaVA, Audio with Whisper).',
    'deliverable': 'Multimodal GraphRAG intelligent system synthesizing knowledge graphs with audio transcription and vision understanding.'
}

P4_AIML_FINETUNING_LLMOPS = {
    'segment': 'ML & Gen AI Engineering',
    'type': 'Core',
    'phase': 'Fine tuning, LLMOPS and Security',
    'duration': '0.5 Month',
    'topics': 'Parameter-Efficient Fine-Tuning (PEFT) & LoRA, Serving LLMs (vLLM, TGI, Quantization) and Token Economics, LLMOPS.',
    'deliverable': 'Domain-adapted LLM fine-tuned using LoRA/PEFT, served via vLLM with 4-bit quantization and token economic budgeting.'
}

P4_AIML_ADV_ML_DL_1 = {
    'segment': 'Advanced ML, Deep Learning & NLP',
    'type': 'Elective',
    'phase': 'Advanced Machine Learning and Deep Learning 1',
    'duration': '1 Month',
    'topics': 'Prob and Stats, Math for ML, Optimisation Theory, Loss Functions, Linear Models, Logistic Regression, Decision Tree and Forests, Support Vector Machines, Clustering, Dimensionality Reduction, Statistical Learning Theory.',
    'deliverable': 'Mathematical derivations and algorithmic implementations of convex optimization, SVM kernel functions, and statistical learning bounds.'
}

P4_AIML_ADV_ML_DL_2 = {
    'segment': 'Advanced ML, Deep Learning & NLP',
    'type': 'Elective',
    'phase': 'Advanced Machine Learning and Deep Learning 2',
    'duration': '1 Month',
    'topics': 'Neural Networks, Model Interpretability, Backpropagation, Advanced NLP - Transformers / GPT, Attention Mechanisms.',
    'deliverable': 'Custom multi-head self-attention mechanism and Transformer encoder-decoder built from first principles with model interpretability.'
}

P4_AIML_DSA = {
    'segment': 'DSA',
    'type': 'Optional',
    'phase': 'DSA for Professionals',
    'duration': '4-6 Months',
    'topics': 'Time and Space Complexity Analysis, Array Problem Solving Patterns (Prefix, Sliding Windows, Subarrays, Subsets, Subsequences), Bit Manipulation, Maths for Problem Solving, Recursion, Backtracking, Sorting, Searching (Binary Search), Two Pointers, Hashing, String Problem Solving Patterns, String Pattern Matching, Linked Lists, Stacks, Queues and Deques, Trees and BST, Tries, Heaps, Greedy, Dynamic Programming, Graphs.',
    'deliverable': 'Rigorous algorithmic problem solving and optimization patterns covering 300+ advanced LeetCode problems for Tier-1 engineering interviews.'
}

P4_AIML_BIG_DATA = {
    'segment': 'Big Data (Recorded)',
    'type': 'Core',
    'phase': 'Big data (Recorded)',
    'duration': '1 Month',
    'topics': 'Hadoop & HDFS, Spark (RDDs, DataFrames, Spark SQL), Spark Streaming & MLlib, Hive & Kafka Integration, Data Visualization (Tableau, AWS QuickSight).',
    'deliverable': 'Scalable distributed batch and stream processing engine using Apache Spark, Kafka, and cloud enterprise visualization dashboards.'
}

P4_AIML_RL = {
    'segment': 'Reinforcement Learning (Recorded)',
    'type': 'Core',
    'phase': 'Reinforcement learning (Recorded)',
    'duration': '1 Month',
    'topics': 'Markov Decision Processes (MDPs), Dynamic Programming (Value & Policy Iteration), Q-Learning & DQN, Policy Gradients & Actor-Critic, PPO, SAC, TD3, Imitation Learning & Multi-Agent RL.',
    'deliverable': 'Autonomous reinforcement learning agent trained in complex environments using Policy Gradients (PPO/SAC) and Actor-Critic architectures.'
}

# Beginner Track Modules: Starts with Generative AI (2 mo) and Python Programming Fundamentals (1 mo)
P4_AIML_GENAI_FOUNDATIONS = {
    'segment': 'Generative AI',
    'type': 'Core',
    'phase': 'Generative AI',
    'duration': '2 Months',
    'topics': 'Generative AI Foundations & the LLM Landscape, Prompt Engineering - Anatomy to Advanced Patterns, AI Reliability - Safety, Evaluation & Power Tools, AI Ecosystems, Productivity & Meeting Intelligence, Knowledge Management & RAG in Practice, Web-Grounded Research & Citations, Building No-Code AI Chatbots, AI for Content Creation, Multimodal GenAI -Images, Video & Voice, Workflow Automation Essentials, Automating with n8n, Automating with Zapier, What Is an AI Agent? Concepts & Live Demos, Tools, Memory & MCP - Agent Building Blocks, Building Agents Without Code, Personal Agents & Multi-Agent Systems, No-Code Coding IDEs - Vibe Coding, Claude Ecosystem Deep-Dive - Skills, Artifacts, claude.md, Prompt Management as a Practice, AI System Design, Evaluation & Observability, Deploying AI Apps - Hosting & Going Live, Deploying AI Apps on AWS.',
    'deliverable': 'Production GenAI workflow automations with n8n/Zapier, multi-agent assistant pipelines with tools & memory, and AWS hosted AI applications.'
}

P4_AIML_PYTHON_FOUNDATIONS = {
    'segment': 'Python Programming Fundamentals',
    'type': 'Core',
    'phase': 'Python Programming Fundamentals',
    'duration': '1 Month',
    'topics': 'Data Types, Variables & Input/Output, Operators, Control Statements, Loops, Functions, Lists, Strings, Sets, Tuples & Dictionaries, Functional Programming, Object-Oriented Programming (OOP), Regular Expressions (Regex), File Handling.',
    'deliverable': 'Modular object-oriented Python software package with regex text parsing, structured file I/O, and automated test coverage.'
}

# Complete Beginner Track (18 modules)
P4_AIML_BEGINNER_MODULES = [
    P4_AIML_GENAI_FOUNDATIONS,
    P4_AIML_PYTHON_FOUNDATIONS,
    P4_AIML_DATA_FOUNDATIONS,
    P4_AIML_SUPERVISED,
    P4_AIML_UNSUPERVISED_TS_REC,
    P4_AIML_NEURAL_NETWORKS,
    P4_AIML_CV_NLP,
    P4_AIML_MLOPS,
    P4_AIML_SYSTEM_DESIGN,
    P4_AIML_FOUNDATIONS_RAG,
    P4_AIML_AGENTIC_PATTERNS,
    P4_AIML_ADVANCED_COGNITIVE,
    P4_AIML_FINETUNING_LLMOPS,
    P4_AIML_ADV_ML_DL_1,
    P4_AIML_ADV_ML_DL_2,
    P4_AIML_DSA,
    P4_AIML_BIG_DATA,
    P4_AIML_RL
]

# Complete Advanced Track (16 modules - skips GenAI 2mo & Python 1mo)
P4_AIML_ADVANCED_MODULES = [
    P4_AIML_DATA_FOUNDATIONS,
    P4_AIML_SUPERVISED,
    P4_AIML_UNSUPERVISED_TS_REC,
    P4_AIML_NEURAL_NETWORKS,
    P4_AIML_CV_NLP,
    P4_AIML_MLOPS,
    P4_AIML_SYSTEM_DESIGN,
    P4_AIML_FOUNDATIONS_RAG,
    P4_AIML_AGENTIC_PATTERNS,
    P4_AIML_ADVANCED_COGNITIVE,
    P4_AIML_FINETUNING_LLMOPS,
    P4_AIML_ADV_ML_DL_1,
    P4_AIML_ADV_ML_DL_2,
    P4_AIML_DSA,
    P4_AIML_BIG_DATA,
    P4_AIML_RL
]



# ==============================================================================
# PROGRAM 5: DEVOPS, CLOUD & AI PLATFORM ENGINEERING - OFFICIAL CURRICULUM
# ==============================================================================

P5_DEVOPS_MODULES = [
    {
        'segment': 'Programming & Scripting',
        'type': 'Core',
        'phase': 'Python',
        'duration': '1 Month',
        'topics': 'Refresher : Introduction To Python and Data Types, Refresher : Operators and Control Statements, Refresher : Iteration : Loops & Iteration Analysis by AI, Refresher : Lab Session on Iteration, Refresher : Functions & Modularity: Designing Code with AI, Refresher : 1D List, Refresher : 2D List, Refresher : Lab Session on List, Refresher : Tuples + Strings, Refresher : Lab Session on Strings, Refresher : Sets and Dictionaries, File & Exception Handling, Interview Problems.',
        'deliverable': 'Automated DevOps Python automation scripts, structured file parsing, CLI tools, and exception-handled server utilities.'
    },
    {
        'segment': 'Operating Systems & Shell',
        'type': 'Core',
        'phase': 'Linux Shell Scripting and Computer Systems 1',
        'duration': '1 Month',
        'topics': 'Linux Essentials, Linux - File Management, Linux - Process Management, Linux - Networks, Linux - Text Processing, Shell scripting introduction, Fundamentals of Shell Scripting.',
        'deliverable': 'Hardened production Linux host with automated system diagnostic scripts, process managers, and text processing utilities.'
    },
    {
        'segment': 'Operating Systems & Shell',
        'type': 'Core',
        'phase': 'Linux Shell Scripting and Computer Systems 2',
        'duration': '1 Month',
        'topics': 'Shell scripting walk through, Shell scripting for DevOps - file management, Shell scripting for DevOps - process management, Shell scripting for DevOps - filesystem management, Shell scripting for DevOps - backup, Shell scripting for DevOps - Networking, Mock interview Demo by instructor, Git introduction, Git in DevOps - GitHook, PR, Branching.',
        'deliverable': 'Production-grade Bash backup & networking automation suite, GitHooks automation, and branching release policies.'
    },
    {
        'segment': 'Containers & Orchestration',
        'type': 'Core',
        'phase': 'DevOps Tools 1',
        'duration': '3 Months',
        'topics': 'Docker introduction, Docker image and Docker containers, Building your own Docker image, Images and Containers Deep dive, Docker volume, Docker networking deep dive, Hardening the Docker env., Demo of implementing industry standard implementation (e.g. in image hardening and other security standards), Introduction to Orchestration, Kubernetes architecture, Kubernetes Pod deep dive, Kubernetes Replicaset and Deployment deep dive, side car, Kubernetes networking, Scaling options in kubernetes - HPA, CA and VPA - compare with Karpentor, Introduction to scaling in kubernets, Network policies, Kubernetes security - RBAC, Kubernetes volumes, Kubernetes ingress, Init Containers, Static Pods, Scheduling, Kubernetes Jobs, Probes, admission controllers, CRD, CNI, Config maps and secrets, Troubleshooting, Deploying a hugging face model on K8s, Introduciton to Observability. Prometheus and Grafana setup, Prometheus Monitoring Configuration, Advanced Monitoring Techniques, Getting Started with Grafana, Variables, Data Sources, and Persistent Dashboards in Grafana, Scaling Grafana: Best Practices, Real-World Use Cases, and Performance Tuning, Deploying your graph in Graphana on a Kubernetes cluster, Advanced observability using Newrelic, Deploying a microservice in Kubernetes cluster project.',
        'deliverable': 'Production Kubernetes cluster with secure container images, HPA autoscaling, Prometheus/Grafana persistent dashboards, and deployed Hugging Face AI model.'
    },
    {
        'segment': 'CI/CD & Configuration Management',
        'type': 'Core',
        'phase': 'DevOps Tools 2',
        'duration': '2 Months',
        'topics': 'Introduction to DevOps, Introduction to CI/CD, Jenkins introduction, architecture, jobs, Project: CI/CD on Jenkins using simple job, Jenkins pipeline syntax walk through, Project: CI/CD on Jenkins using pipelines, Jenkins advanced - add nodes, RBAC, Project by engineers on Jenkins end to cicd in industry standard., Introduction to GitHub Actions, Secrets, Events, and Workflow Optimization, Advanced Techniques and Best Practices, Efficient Workflows and Security Practices, Project by engineers on GitHub actions end to cicd in industry standard., Advanced ArgoCD Usage and Configuration, Advanced Features and Integration, ArgoCD-Jenkins Integration, Project Demo, IaC fundamentals and Ansible Fundamentals, Ansible Playbooks & Modules, Templates, Variables & Facts, Roles & Advanced Topics, Ansible Vault & Best Practices, Introduction to SRE concepts, Ansible Project.',
        'deliverable': 'End-to-end multi-stage CI/CD pipeline using GitHub Actions, Jenkins RBAC, ArgoCD GitOps declarative deployments, and Ansible infrastructure playbooks.'
    },
    {
        'segment': 'Cloud Infrastructure (AWS)',
        'type': 'Core',
        'phase': 'AWS 1',
        'duration': '1.5 Months',
        'topics': 'Cloud Basics & Evolution, AWS Compute & EC2 Intro, EC2 Deep Dive, EC2 Hosting & Load Balancing, AWS IAM Basics, AWS Storage & CloudFront, S3 Deep Dive, AWS CLI & Boto Intro, AWS VPC & Networking Basics, Advanced AWS Networking, AWS Observability & CloudWatch, CloudWatch & CloudTrail Advanced, Docker App on EC2 Project, AWS Lambda & API Gateway, End-to-End Project.',
        'deliverable': 'Highly available VPC infrastructure across multiple AZs with ALB load balancing, CloudWatch observability, and serverless API Gateway + Lambda endpoints.'
    },
    {
        'segment': 'Cloud Infrastructure & IaC (AWS)',
        'type': 'Core',
        'phase': 'AWS 2',
        'duration': '3 Months',
        'topics': 'AWS ECS & ECR Intro, ECS Fundamental, EKS Basics, EKS Advanced, Microservices on AWS Project, AWS CI/CD & Pipelines, Querying AWS Services, Serverless on AWS, AWS Cloud Formation, AWS Security: Identity & Network, AWS Security: Data & Detection, AWS Security Hands-on, AWS Control Tower, AWS RDS (SQL Databases), DynamoDB (NoSQL), AWS Data Engineering (Glue & Athena), AWS Migration Services, AWS Sagemaker, Generative AI on AWS, AWS Services Deep Dive, Project Architecture Review, Kubernetes AI Project, AWS Backup, DevOps Cert Discussion, Terraform & IaC Intro, Terraform Language Deep Dive, Terraform State & Modules, Terraform Dependencies, Advanced Terraform Workspaces, Terraform Cluster Project, Deploying an app - Project.',
        'deliverable': '1-Click Terraform IaC cloud deployment of EKS Kubernetes cluster, RDS/DynamoDB databases, SageMaker AI integration, and multi-account Control Tower security.'
    },
    {
        'segment': 'Platform SRE & Governance',
        'type': 'Elective',
        'phase': 'Observability, Security & Responsible Systems',
        'duration': '1.5 Months',
        'topics': 'Introduction to Observability, Security & Responsible Systems, Observability for AI and Operations, Designing ML-Ready Pipelines, Machine-Readable Observability Layer, Anomaly Detection Systems, Feature Engineering & Alerting, Behavioral Fingerprinting, Predictive Operations & Failure Prevention, Forecasting & Early Warning, Security Foundations for AI & Automation, Guardrails & Access Control, Zero-Trust & Audit, AI Threat Models, PII & Model Integrity, Prompt Injection & Testing, Governance and Responsible AI, Audit, Compliance & Ethics.',
        'deliverable': 'Zero-trust predictive observability platform with AI threat modeling, automated anomaly detection, and SOC2/GDPR compliance guardrails.'
    },
    {
        'segment': 'AI Platform Engineering',
        'type': 'Elective',
        'phase': 'ML Systems, MLOps & DataOps',
        'duration': '1 Month',
        'topics': 'Introduction to ML Systems and DataOps, AI Observability and Model Health, Drift Detection & Monitoring, Model Health & Retraining, ML-Driven Optimization, Autoscaling & Cost Engineering, MLOps on Kubernetes, Inference & GPU Operations, End-to-End MLOps Build, Dataset Operations (DataOps), Data Quality & Governance.',
        'deliverable': 'Production MLOps pipeline on Kubernetes with GPU autoscaling, data drift detection, and automated model retraining triggers.'
    },
    {
        'segment': 'Agentic AI & LLMOps',
        'type': 'Elective',
        'phase': 'Generative AI & Agentic Systems',
        'duration': '1 Month',
        'topics': 'Introduction to Gen AI, Generative AI for Engineers, IaC Generation & Validation, Safe GenAI in Production, Retrieval-Augmented Generation (RAG), Building RAG Systems, RAG Quality & Strategy, Agentic AI Systems, Multi-Agent Architecture, Agent Testing & Human-in-the-Loop, LLM Gateway and Proxy Patterns, Caching, Filtering & Cost Control.',
        'deliverable': 'Enterprise LLM Gateway with semantic caching, proxy rate limiting, and multi-agent RAG workflow with human-in-the-loop validation.'
    },
    {
        'segment': 'No-Code / Low-Code AI Agents',
        'type': 'Elective',
        'phase': 'AI & Agents: From Talking to AI to Building One',
        'duration': '1 Month',
        'topics': 'GenAI World & LLM Landscape, Prompt Engineering Basics, Advanced Prompting & AI Safety Basics, LLM Built-in Power Tools, RAG, n8n Automation Workflow, What Is an AI Agent?, Building Agents with n8n, OpenClaw: Personal 24/7 AI Agent, Multi-Agent Systems, MindStudio: Building AI Apps Visually.',
        'deliverable': 'Autonomous 24/7 AI agent running via n8n automation and MindStudio visual workflows.'
    },
    {
        'segment': 'Data Structures & Algorithms',
        'type': 'Elective',
        'phase': 'Intermediate DSA : AI Assisted Problem Solving',
        'duration': '1 Month',
        'topics': 'Time Complexity, Arrays & Basics of AI, Lab Session on TC/SC/Output & Debugging, Prefix Sum & Carry Forward with AI-Assisted Problem Solving, Arrays techniques & smart prompting, Memory Management & Sorting Basics, Bit Manipulation Basics, 2D Matrices, Strings & Immutability visualisations through AI, Contest.',
        'deliverable': 'Foundational algorithmic problem-solving with AI-assisted optimization and prefix sum / matrix techniques.'
    },
    {
        'segment': 'Data Structures & Algorithms',
        'type': 'Elective',
        'phase': 'Advanced DSA: Foundations:Core Techniques & Optimization',
        'duration': '1 Month',
        'topics': 'DSA: Time Complexity, DSA: Arrays Techniques, DSA: Arrays 1: One Dimensional, DSA: Arrays 2: Two Dimensional, DSA: Lab Session on Arrays, DSA: Bit Manipulation, DSA: Lab Session on Bit Manipulation, DSA: Recursion, DSA: Lab Session on Recursion, DSA: Maths: Modular Arithmetic & GCD, DSA: Hashing, DSA: Lab Session on Hashing, DSA: Sorting 1: Count Sort & Merge Sort, DSA: Sorting 2: Quick Sort & Comparator Problems, DSA: Sample Contest: Dual Camera Proctoring, DSA Contest 1: Arrays, Bit Manipulation, Recursion, Math, Hashing & Sorting.',
        'deliverable': 'Mastery of recursion, bit manipulation, modular arithmetic, and sorting / hashing algorithmic patterns.'
    },
    {
        'segment': 'Data Structures & Algorithms',
        'type': 'Elective',
        'phase': 'Advanced DSA: Linear & Non-Linear Data Structures',
        'duration': '1 Month',
        'topics': 'DSA: Searching 1: Binary Search on Array, DSA: Searching 2: Binary Search on Answer, DSA: Lab Session on Searching, DSA: Classes, Objects & Linked List Introduction, DSA: Linked List: Basic Problems, DSA: Stacks, DSA: Lab Session on Stacks, DSA: Queues: Implementation & Problems, DSA: Trees 1: Structure & Traversal, DSA: Trees 2: BST, DSA: Lab Session on Binary Trees, DSA: Revision of DSA 1 & 2, DSA: Break, DSA Contest 2: Searching, Linked List, Stacks, Queues & Trees.',
        'deliverable': 'Binary search, linked lists, stack/queue memory primitives, and binary search tree traversals.'
    },
    {
        'segment': 'Data Structures & Algorithms',
        'type': 'Elective',
        'phase': 'Advanced DSA: Backtracking & Advanced Trees',
        'duration': '1 Month',
        'topics': 'DSA: Maths: Combinatorics Basics & Prime Numbers, DSA: Lab Session on Prime Numbers & 2 Pointers, DSA: Lab Session on Maths & 2 Pointers, DSA: Backtracking, DSA: Lab Session on Backtracking, DSA: Linked List: Sorting and Problems, DSA: Linked List: Doubly Linked List & Detecting Loop, DSA: Trees 4: Morris Inorder Traversal + LCA, DSA: Lab Session on Binary Trees 2, DSA: Hashing 3: Internal Implementation & Problems, DSA Contest 3: Math, Two Pointers, Backtracking, Linked List & Trees.',
        'deliverable': 'Combinatorics, state-space backtracking, Morris traversals, and LCA tree algorithms.'
    },
    {
        'segment': 'Data Structures & Algorithms',
        'type': 'Elective',
        'phase': 'Advanced DSA: DP, Heaps & Graphs - Crack It with AI Edge',
        'duration': '1 Month',
        'topics': 'DSA: Heaps: Introduction, DSA: Heap Sort & Greedy, DSA: Lab Session on Heaps & Greedy, DSA: Lab Session on Interview Problems 1, DSA: DP 1: One Dimensional, DSA: DP 2: Two Dimensional, DSA: DP 3: Knapsack, DSA: Lab Session on Applications of Knapsack, DSA: Graphs 1: Introduction, DFS & Cycle Detection, DSA: Graphs 2: BFS & MST, DSA: Graphs 3: Dijkstra Algo & Topological Sort, DSA: Lab Session on Interview Problems 2, DSA: Revision of DSA 3 & 4, DSA Contest 4: Heaps, Greedy, DP & Graphs, Mandatory Skill Evaluation Test: DSA, Skill Evaluation Test Discussion + How to ace DSA Interview, DSA : Real World Project 1 (Social Network Analyzer), DSA : Real world Project 2 ( Invoice Merger ).',
        'deliverable': 'Dynamic programming, Dijkstra graph routing, MST, and real-world system projects (Social Network Analyzer & Invoice Merger).'
    },
    {
        'segment': 'High-Level System Design',
        'type': 'Elective',
        'phase': 'Distributed System Design & AI-Integrated Architectures',
        'duration': '1.5 Months',
        'topics': 'System Design Foundations & Modern Infrastructure, Load Balancing, Consistent Hashing & Traffic Routing at Scale, Caching Systems: CDN, Backend Caches, Cache Invalidation, Case Study: Caching at Scale (Scaler Code Judge and Contest Leaderboards + AI Workloads), Case Study: Caching Facebook News Feed, CAP / PACELC theorem + Master Slave Replication, SQL vs NoSQL + Sharding, Database Orchestration & Shard Creation, Case study: Google Typeahead (How to approach System Design Problems), Case Study: Google Typeahead (Design and Optimizations), NoSQL Internals - LSM Tree and Multi Master, Case Study: Messaging Apps (FB Messenger, Whatsapp, Slack), Messaging Queues - Apache Kafka & Zookeeper, Case Study: ElasticSearch (Full Text Search), Case Study: S3, HDFS (Large File Storage), Case Study: Uber (Nearest Neighbor Search), Case Study: Rate Limiter + Unique ID Generator (Infra), Case Study: OTT Platform (OTT), Microservices - 1, Microservices - 2, Case Study: Ecommerce Platform (Microservices).',
        'deliverable': 'Architectural blueprint of high-throughput distributed systems: consistent hashing, Kafka event streaming, LSM-tree NoSQL stores, and Uber/Netflix scale services.'
    }
]


def resolve_program_code(prog_val):
    if not prog_val:
        return 'P1_ACADEMY'
    p = str(prog_val).upper().strip()
    if 'P2' in p or 'DSML' in p or 'DATA SCIENCE' in p:
        return 'P2_DSML'
    elif 'P3' in p or 'FDE' in p or 'FORWARD' in p:
        return 'P3_FDE'
    elif 'P4' in p or 'AGENTIC' in p:
        return 'P4_AIML_AGENTIC'
    elif 'P5' in p or 'DEVOPS' in p or 'CLOUD' in p or 'PLATFORM' in p:
        return 'P5_DEVOPS_CLOUD'
    elif 'P1' in p or 'ACADEMY' in p or 'SOFTWARE' in p:
        return 'P1_ACADEMY'
    return 'P1_ACADEMY'


def get_program_career_pathways(program_name, track_name=None):
    """
    Returns real-world and catalog-grounded career pathways, job roles, salary bands,
    and transition context tailored to each Scaler program and track.
    """
    p_low = str(program_name or '').lower()
    t_low = str(track_name or '').lower()
    
    # 1. Program 1: Scaler Academy (Software & AI Engineering)
    if 'academy' in p_low or 'software' in p_low or 'p1' in p_low:
        if 'advanced' in t_low or 'high-level' in t_low or 'system design' in t_low or 'scalability' in t_low or 'architecture' in t_low:
            return {
                'roles': ['Senior SDE (SDE 3)', 'Staff Software Engineer', 'Technical Lead / Tech Lead', 'Distributed Systems Architect', 'Engineering Manager'],
                'salary_range': '₹28 LPA – ₹65+ LPA',
                'transition_summary': 'High-Level System Design (HLD), distributed caching, Kafka event streaming, and engineering leadership for large-scale production architectures.'
            }
        elif 'intermediate' in t_low or 'backend' in t_low or 'algorithms' in t_low or 'lld' in t_low or 'transition' in t_low or 'dsa' in t_low:
            return {
                'roles': ['Software Development Engineer II (SDE 2)', 'Backend Microservices Engineer', 'Full-Stack SDE', 'Java / C++ / Go Software Engineer'],
                'salary_range': '₹16 LPA – ₹32 LPA',
                'transition_summary': 'Core product-company transition mastering Advanced DSA, Low-Level Object-Oriented Design (LLD), and scalable backend architectures.'
            }
        else:
            return {
                'roles': ['Junior Software Engineer (SDE 1)', 'Associate Software Developer', 'Full-Stack Developer', 'Backend Developer'],
                'salary_range': '₹8 LPA – ₹18 LPA',
                'transition_summary': 'Ground-zero algorithmic problem-solving and software development foundations designed for non-tech switchers, freshers, and non-CS graduates.'
            }

    # 2. Program 2: DSML (Modern Data Science & Machine Learning)
    elif 'dsml' in p_low or 'data science' in p_low or ('machine learning' in p_low and 'agentic' not in p_low and 'p4' not in p_low):
        if 'advanced' in t_low or 'production ml' in t_low:
            return {
                'roles': ['Senior Data Scientist', 'Machine Learning Engineer (MLE)', 'MLOps Engineer', 'Computer Vision / NLP Specialist', 'Lead Data Scientist'],
                'salary_range': '₹25 LPA – ₹55+ LPA',
                'transition_summary': 'Deep learning neural architectures, transformer models, enterprise recommendation engines, and production MLOps deployment.'
            }
        elif 'core' in t_low or 'intermediate' in t_low or 'applied' in t_low or 'analytics & machine' in t_low:
            return {
                'roles': ['Applied Machine Learning Engineer', 'Data Scientist', 'Statistical Modeler', 'Quantitative Analyst', 'Data Science Consultant'],
                'salary_range': '₹15 LPA – ₹30 LPA',
                'transition_summary': 'Statistical hypothesis testing, applied supervised/unsupervised ML algorithms, and end-to-end data science pipelines.'
            }
        else:
            return {
                'roles': ['Data Analyst', 'Product Analyst', 'Business Intelligence Engineer (BIE)', 'Growth Analytics Lead', 'Analytics Consultant'],
                'salary_range': '₹8 LPA – ₹20 LPA',
                'transition_summary': 'SQL, Python data manipulation, Tableau dashboards, and business ML modeling translating business domain knowledge into analytical leadership.'
            }

    # 3. Program 3: AI Forward Deployed Engineer (FDE)
    elif 'fde' in p_low or 'forward deployed' in p_low or 'p3' in p_low:
        return {
            'roles': ['AI Forward Deployed Engineer (FDE)', 'Enterprise AI Solutions Architect', 'Production RAG & LLM Integration Specialist', 'Client AI Systems Engineer', 'Technical AI Engagement Lead'],
            'salary_range': '₹25 LPA – ₹60+ LPA',
            'transition_summary': 'High-impact customer-facing engineering deploying production RAG, vector search, custom fine-tuning, and enterprise autonomous agent workflows.'
        }

    # 4. Program 4: AI & Machine Learning with Agentic AI
    elif 'agentic' in p_low or 'p4' in p_low:
        if 'beginner' in t_low or 'foundation' in t_low:
            return {
                'roles': ['AI Application Developer', 'Applied AI Solutions Specialist', 'Prompt & Agentic Workflow Engineer'],
                'salary_range': '₹12 LPA – ₹24 LPA',
                'transition_summary': 'Foundational machine learning, AI coding assistants, and prompt-driven autonomous workflow development.'
            }
        else:
            return {
                'roles': ['Agentic AI Systems Engineer', 'Autonomous Multi-Agent Architect', 'Foundation Model & LLMOps Engineer', 'Generative AI R&D Specialist', 'Deep Learning Architect'],
                'salary_range': '₹28 LPA – ₹70+ LPA',
                'transition_summary': 'Multi-agent swarm orchestration (LangGraph, CrewAI), fine-tuning frontier models, and autonomous tool-calling systems.'
            }

    # 5. Program 5: DevOps, Cloud & AI Platform Engineering
    elif 'devops' in p_low or 'cloud' in p_low or 'platform' in p_low or 'p5' in p_low:
        if 'sre' in t_low or 'reliability' in t_low or 'kubernetes' in t_low:
            return {
                'roles': ['Site Reliability Engineer (SRE)', 'DevSecOps Engineer', 'Kubernetes & Platform Architect', 'MLOps Infrastructure Engineer', 'Principal Cloud Architect'],
                'salary_range': '₹20 LPA – ₹48+ LPA',
                'transition_summary': 'Multi-node Kubernetes clustering, distributed observability (Prometheus/Grafana), DevSecOps governance, and AI infrastructure.'
            }
        else:
            return {
                'roles': ['Cloud Infrastructure Engineer', 'DevOps Engineer', 'Cloud Automation Specialist', 'AWS / Cloud Platform Engineer'],
                'salary_range': '₹10 LPA – ₹22 LPA',
                'transition_summary': 'Automated CI/CD pipelines, Docker containerization, Infrastructure as Code (Terraform), and enterprise cloud deployments.'
            }

    # Default fallback
    return {
        'roles': ['Software Engineer', 'Technical Specialist', 'Engineering Lead'],
        'salary_range': '₹12 LPA – ₹30 LPA',
        'transition_summary': 'Industry-aligned technical skill enhancement and high-growth technology career acceleration.'
    }


def get_market_intelligence(arg1="", arg2="", arg3="", arg4="", track_name=""):
    """
    Returns official catalogue URLs, track-tailored curriculum modules, and career options.
    If Scaler Academy (P1) or DSML (P2) is selected, returns the precise modules for
    the candidate's assigned track (Beginner, Intermediate, or Advanced).
    """
    # 1. Resolve program code
    if any(k in str(arg1).upper() for k in ['P1', 'P2', 'P3', 'P4', 'P5', 'ACADEMY', 'DSML', 'DATA SCIENCE', 'DEVOPS', 'FDE', 'AGENTIC', 'PROGRAM']):
        p_code = resolve_program_code(arg1)
    elif any(k in str(arg4).upper() for k in ['P1', 'P2', 'P3', 'P4', 'P5', 'ACADEMY', 'DSML', 'DATA SCIENCE', 'DEVOPS', 'FDE', 'AGENTIC', 'PROGRAM']):
        p_code = resolve_program_code(arg4)
    else:
        p_code = resolve_program_code(arg1)

    p_data = PROGRAM_CATALOG_DATA.get(p_code, PROGRAM_CATALOG_DATA['P1_ACADEMY'])

    # 2. Track-specific resolution for Scaler Academy (P1)
    if p_code == 'P1_ACADEMY':
        all_text = f"{str(track_name)} {str(arg1)} {str(arg2)} {str(arg3)} {str(arg4)}".lower()
        t_low = str(track_name).lower() if track_name else ''

        if 'advanced' in t_low or 'system design' in t_low or 'scalability' in t_low or 'architecture' in t_low:
            selected_modules = P1_ACADEMY_ADVANCED_MODULES
            track_label = 'Advanced Track'
        elif 'intermediate' in t_low or 'dsa core' in t_low or 'sde transition' in t_low or 'algorithms & lld' in t_low:
            selected_modules = P1_ACADEMY_INTERMEDIATE_MODULES
            track_label = 'Intermediate Track'
        elif 'beginner' in t_low or 'foundation' in t_low or 'problem solving' in t_low:
            selected_modules = P1_ACADEMY_BEGINNER_MODULES
            track_label = 'Beginner Track'
        else:
            # Fallback to experience-based tier if track_name is generic
            try:
                exp_num = float(str(arg3).replace('years', '').replace('yrs', '').replace('+', '').strip())
                if exp_num >= 5.0:
                    selected_modules = P1_ACADEMY_ADVANCED_MODULES
                    track_label = 'Advanced Track'
                elif exp_num >= 2.0:
                    selected_modules = P1_ACADEMY_INTERMEDIATE_MODULES
                    track_label = 'Intermediate Track'
                else:
                    selected_modules = P1_ACADEMY_BEGINNER_MODULES
                    track_label = 'Beginner Track'
            except Exception:
                selected_modules = P1_ACADEMY_BEGINNER_MODULES
                track_label = 'Beginner Track'

        resolved_track = str(track_name) if track_name else track_label
        return {
            'program_name': p_data['program_name'],
            'catalogue_url': p_data['catalogue_url'],
            'top_hiring_companies': p_data.get('top_hiring_companies', []),
            'curriculum_modules': selected_modules,
            'track_label': resolved_track,
            'career_options': get_program_career_pathways(p_data['program_name'], resolved_track)
        }

    # 3. Track-specific resolution for Modern Data Science & ML (P2)
    if p_code == 'P2_DSML':
        t_low = str(track_name).lower() if track_name else ''
        all_text = f"{str(track_name)} {str(arg1)} {str(arg2)} {str(arg3)} {str(arg4)}".lower()

        if 'intermediate' in t_low or 'core analytics' in t_low or 'machine learning' in t_low or 'predictive' in t_low or 'specialization' in t_low:
            selected_modules = P2_DSML_INTERMEDIATE_MODULES
            track_label = 'Intermediate Track (Core ML & AI Engineering)'
        elif 'beginner' in t_low or 'python prep' in t_low or 'foundation' in t_low or 'business ml' in t_low or 'data analytics' in t_low:
            selected_modules = P2_DSML_BEGINNER_MODULES
            track_label = 'Beginner Track (Data Analytics, Python & Business ML)'
        else:
            # Fallback based on experience
            try:
                exp_num = float(str(arg3).replace('years', '').replace('yrs', '').replace('+', '').strip())
                if exp_num >= 2.0:
                    selected_modules = P2_DSML_INTERMEDIATE_MODULES
                    track_label = 'Intermediate Track (Core ML & AI Engineering)'
                else:
                    selected_modules = P2_DSML_BEGINNER_MODULES
                    track_label = 'Beginner Track (Data Analytics, Python & Business ML)'
            except Exception:
                selected_modules = P2_DSML_BEGINNER_MODULES
                track_label = 'Beginner Track (Data Analytics, Python & Business ML)'

        resolved_track = str(track_name) if track_name else track_label
        return {
            'program_name': p_data['program_name'],
            'catalogue_url': p_data['catalogue_url'],
            'top_hiring_companies': p_data.get('top_hiring_companies', []),
            'curriculum_modules': selected_modules,
            'track_label': resolved_track,
            'career_options': get_program_career_pathways(p_data['program_name'], resolved_track)
        }

    # 4. Track-specific resolution for AI Forward Deployed Engineer (P3)
    if p_code == 'P3_FDE':
        resolved_track = str(track_name) if track_name else 'AI Forward Deployed Engineer Track'
        return {
            'program_name': p_data['program_name'],
            'catalogue_url': p_data['catalogue_url'],
            'top_hiring_companies': p_data.get('top_hiring_companies', []),
            'curriculum_modules': P3_FDE_MODULES,
            'track_label': resolved_track,
            'career_options': get_program_career_pathways(p_data['program_name'], resolved_track)
        }

    # 5. Track-specific resolution for AI & Machine Learning with Agentic AI (P4)
    if p_code == 'P4_AIML_AGENTIC':
        t_low = str(track_name).lower() if track_name else ''
        all_text = f"{str(track_name)} {str(arg1)} {str(arg2)} {str(arg3)} {str(arg4)}".lower()

        if 'beginner' in t_low or 'foundation' in t_low or 'math prep' in t_low:
            selected_modules = P4_AIML_BEGINNER_MODULES
            track_label = 'Beginner Track (AI & Machine Learning Foundations)'
        elif 'advanced' in t_low or 'agentic' in t_low or 'applied ai' in t_low or 'core machine learning' in t_low or 'autonomous' in t_low or 'specialization' in t_low:
            selected_modules = P4_AIML_ADVANCED_MODULES
            track_label = 'Advanced Track (Agentic AI & LLMOps)'
        else:
            # Fallback based on experience
            try:
                exp_num = float(str(arg3).replace('years', '').replace('yrs', '').replace('+', '').strip())
                if exp_num >= 2.0:
                    selected_modules = P4_AIML_ADVANCED_MODULES
                    track_label = 'Advanced Track (Agentic AI & LLMOps)'
                else:
                    selected_modules = P4_AIML_BEGINNER_MODULES
                    track_label = 'Beginner Track (AI & Machine Learning Foundations)'
            except Exception:
                selected_modules = P4_AIML_BEGINNER_MODULES
                track_label = 'Beginner Track (AI & Machine Learning Foundations)'

        resolved_track = str(track_name) if track_name else track_label
        return {
            'program_name': p_data['program_name'],
            'catalogue_url': p_data['catalogue_url'],
            'top_hiring_companies': p_data.get('top_hiring_companies', []),
            'curriculum_modules': selected_modules,
            'track_label': resolved_track,
            'career_options': get_program_career_pathways(p_data['program_name'], resolved_track)
        }

    # 6. Track-specific resolution for DevOps, Cloud & AI Platform Engineering (P5)
    if p_code == 'P5_DEVOPS_CLOUD':
        resolved_track = str(track_name) if track_name else 'Cloud Architecture, SRE & AI Platform Track'
        return {
            'program_name': p_data['program_name'],
            'catalogue_url': p_data['catalogue_url'],
            'top_hiring_companies': p_data.get('top_hiring_companies', []),
            'curriculum_modules': P5_DEVOPS_MODULES,
            'track_label': resolved_track,
            'career_options': get_program_career_pathways(p_data['program_name'], resolved_track)
        }

    # Fallback return
    resolved_track = str(track_name) if track_name else 'Standard Track'
    return {
        'program_name': p_data['program_name'],
        'catalogue_url': p_data['catalogue_url'],
        'top_hiring_companies': p_data.get('top_hiring_companies', []),
        'curriculum_modules': p_data.get('curriculum_modules', []),
        'track_label': resolved_track,
        'career_options': get_program_career_pathways(p_data['program_name'], resolved_track)
    }

def get_all_curricula_catalog():
    return {
        'P1_ACADEMY_BEGINNER': P1_ACADEMY_BEGINNER_MODULES,
        'P1_ACADEMY_INTERMEDIATE': P1_ACADEMY_INTERMEDIATE_MODULES,
        'P1_ACADEMY_ADVANCED': P1_ACADEMY_ADVANCED_MODULES,
        'P2_DSML_BEGINNER': P2_DSML_BEGINNER_MODULES,
        'P2_DSML_INTERMEDIATE': P2_DSML_INTERMEDIATE_MODULES,
        'P3_FDE': P3_FDE_MODULES,
        'P4_AIML_BEGINNER': P4_AIML_BEGINNER_MODULES,
        'P4_AIML_ADVANCED': P4_AIML_ADVANCED_MODULES,
        'P5_DEVOPS': P5_DEVOPS_MODULES
    }

