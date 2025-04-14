// Interview Chat AI Simulator
// This script simulates an AI assistant with knowledge about interviews

document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const messagesContainer = document.getElementById('messages');
    const clearBtn = document.querySelector('.clear-btn');

    // AI Interview Assistant API
    const InterviewAI = {
        // Conversation context and memory
        context: {
            conversationHistory: [],
            userInfo: {
                name: null,
                targetRole: null,
                experience: null
            },
            interviewStage: 'introduction', // introduction, questions, feedback
            questionCount: 0,
            lastQuestionType: null,
            topicsFocused: new Set()
        },

        // Interview question bank
        questionBank: {
            behavioral: [
                "Tell me about a time when you had to deal with a difficult team member.",
                "Describe a situation where you had to make a decision with limited information.",
                "Tell me about a project that didn't go as planned. How did you handle it?",
                "Give me an example of a time you showed leadership skills.",
                "Describe a situation where you had to meet a tight deadline.",
                "Tell me about a time you received critical feedback and how you responded to it.",
                "Describe a situation where you had to resolve a conflict at work."
            ],
            technical: [
                "How would you design a system that needs to handle high traffic?",
                "Explain how you would approach debugging a complex issue in production.",
                "What factors do you consider when selecting technologies for a new project?",
                "How do you stay updated with the latest trends in your field?",
                "Describe your process for ensuring code quality.",
                "How would you optimize a slow-performing application?"
            ],
            personal: [
                "What are your greatest strengths?",
                "What do you consider to be your weaknesses?",
                "Where do you see yourself in five years?",
                "Why do you want to work for this company?",
                "What motivates you in your work?",
                "Tell me about yourself.",
                "Why should we hire you for this position?"
            ],
            situational: [
                "How would you handle a situation where you disagree with your manager's approach?",
                "What would you do if you were assigned a task but weren't given enough resources?",
                "How would you prioritize competing deadlines?",
                "What would you do if a team member wasn't contributing their fair share?",
                "How would you handle receiving an unrealistic deadline for an important project?"
            ],
            curveball: [
                "If you were an animal, what would you be and why?",
                "How many windows are there in New York City?",
                "Sell me this pen.",
                "If you could have dinner with anyone from history, who would it be and why?"
            ]
        },

        // Response generation methods
        init() {
            this.context.conversationHistory = [];
            this.context.interviewStage = 'introduction';
            this.context.questionCount = 0;
            this.context.topicsFocused.clear();
            return this.getWelcomeMessage();
        },

        processInput(input) {
            // Add message to conversation history
            this.context.conversationHistory.push({
                role: 'user',
                content: input
            });

            // Extract information about the user if available
            this.extractUserInfo(input);

            // Determine appropriate response based on context
            let response;
            
            if (this.context.interviewStage === 'introduction') {
                response = this.handleIntroductionStage(input);
            } else if (this.context.interviewStage === 'questions') {
                response = this.handleQuestionsStage(input);
            } else if (this.context.interviewStage === 'feedback') {
                response = this.handleFeedbackStage(input);
            }

            // If no specific handler caught it, use the fallback response
            if (!response) {
                response = this.generateGenericResponse(input);
            }

            // Add AI response to conversation history
            this.context.conversationHistory.push({
                role: 'assistant',
                content: response
            });

            return response;
        },

        extractUserInfo(input) {
            const lowerInput = input.toLowerCase();
            
            // Try to extract name
            const nameMatch = lowerInput.match(/my name is ([a-z]+)/i) || 
                            lowerInput.match(/i am ([a-z]+)/i) ||
                            lowerInput.match(/i'm ([a-z]+)/i);
            if (nameMatch && !this.context.userInfo.name) {
                this.context.userInfo.name = nameMatch[1].charAt(0).toUpperCase() + nameMatch[1].slice(1);
            }
            
            // Try to extract target role
            const roleMatch = lowerInput.match(/for (a|an) ([a-z\s]+) position/i) || 
                           lowerInput.match(/applying for ([a-z\s]+)/i) ||
                           lowerInput.match(/role as (a|an) ([a-z\s]+)/i) ||
                           lowerInput.match(/job as (a|an) ([a-z\s]+)/i);
            if (roleMatch && !this.context.userInfo.targetRole) {
                this.context.userInfo.targetRole = roleMatch[roleMatch.length - 1];
            }
            
            // Try to extract experience level
            const expMatch = lowerInput.match(/([0-9]+) years? of experience/i) ||
                          lowerInput.match(/experience of ([0-9]+) years?/i) ||
                          lowerInput.match(/i have ([0-9]+) years?/i);
            if (expMatch && !this.context.userInfo.experience) {
                this.context.userInfo.experience = parseInt(expMatch[1]);
            }
        },

        handleIntroductionStage(input) {
            const lowerInput = input.toLowerCase();
            
            // Check if user wants to start the interview
            if (containsAny(lowerInput, ['start interview', 'begin interview', 'let\'s start', 'ready to start'])) {
                this.context.interviewStage = 'questions';
                return this.startInterviewQuestions();
            }
            
            // Check if user is asking about the interview process
            if (containsAny(lowerInput, ['how does this work', 'what should i do', 'how do we start', 'what is this'])) {
                return "I'm your AI interview coach. I can conduct a mock interview, provide feedback on your answers, or answer questions about interviewing techniques. Would you like to start a practice interview, or do you have specific questions about interviewing?";
            }
            
            // If user is introducing themselves, acknowledge and offer to start
            if (containsAny(lowerInput, ['my name is', 'i am', 'i\'m']) && this.context.userInfo.name) {
                return `Nice to meet you, ${this.context.userInfo.name}! Are you ready to start your interview practice? I'll ask you a series of questions similar to what you might encounter in a real interview.`;
            }
            
            // Default introduction response
            return "Hello! I'm your AI interview assistant. I can simulate a job interview to help you practice, or answer questions about interview techniques. Would you like to start a practice interview?";
        },

        handleQuestionsStage(input) {
            // Check if they're answering a question
            if (this.context.lastQuestionType) {
                // Evaluate their answer
                const feedback = this.evaluateAnswer(input, this.context.lastQuestionType);
                
                // Increment question count
                this.context.questionCount++;
                
                // If we've asked enough questions, move to feedback stage
                if (this.context.questionCount >= 5) {
                    this.context.interviewStage = 'feedback';
                    return feedback + "\n\nWe've completed a good set of practice questions. " + 
                           "Would you like to receive overall feedback on the interview, or would you prefer to continue with more questions?";
                }
                
                // Ask another question
                const nextQuestion = this.getNextQuestion();
                return feedback + "\n\n" + nextQuestion;
            }
            
            // If no question has been asked yet, start with one
            return this.startInterviewQuestions();
        },

        handleFeedbackStage(input) {
            const lowerInput = input.toLowerCase();
            
            // Check if they want more questions
            if (containsAny(lowerInput, ['more questions', 'continue', 'ask more', 'next question'])) {
                this.context.interviewStage = 'questions';
                return this.getNextQuestion();
            }
            
            // Check if they want to end the interview
            if (containsAny(lowerInput, ['end', 'finish', 'done', 'that\'s all', 'complete'])) {
                return this.generateOverallFeedback();
            }
            
            // If they're asking for specific feedback
            if (containsAny(lowerInput, ['feedback', 'how did i do', 'performance', 'improve'])) {
                return this.generateOverallFeedback();
            }
            
            // Default feedback stage response
            return "I hope you found this practice session helpful. Would you like me to provide overall feedback on your performance, continue with more questions, or end the interview?";
        },

        startInterviewQuestions() {
            this.context.interviewStage = 'questions';
            
            let introduction = '';
            if (this.context.userInfo.name) {
                introduction = `Great, ${this.context.userInfo.name}! `;
            }
            
            if (this.context.userInfo.targetRole) {
                introduction += `I'll ask you questions relevant to a ${this.context.userInfo.targetRole} position. `;
            } else {
                introduction += "I'll ask you a variety of interview questions commonly asked in job interviews. ";
            }
            
            introduction += "Let's begin with a common question:\n\n";
            
            const firstQuestion = this.getNextQuestion();
            return introduction + firstQuestion;
        },

        getNextQuestion() {
            // Select question type
            const questionTypes = ['behavioral', 'technical', 'personal', 'situational'];
            let questionType;
            
            // Ensure varied question types
            do {
                questionType = questionTypes[Math.floor(Math.random() * questionTypes.length)];
            } while (questionType === this.context.lastQuestionType && this.context.questionCount < 3);
            
            // Add a curve ball question if we're at question 3 or 4
            if ((this.context.questionCount === 3 || this.context.questionCount === 4) && 
                !this.context.topicsFocused.has('curveball')) {
                questionType = 'curveball';
            }
            
            // Get questions of the selected type
            const questions = this.questionBank[questionType];
            const question = questions[Math.floor(Math.random() * questions.length)];
            
            // Update context
            this.context.lastQuestionType = questionType;
            this.context.topicsFocused.add(questionType);
            
            return question;
        },

        evaluateAnswer(answer, questionType) {
            // Length-based evaluation (simple heuristic)
            const wordCount = answer.split(/\s+/).length;
            let lengthFeedback = '';
            
            if (wordCount < 20) {
                lengthFeedback = "Your answer was quite brief. In interviews, it's important to provide enough detail to fully address the question while staying concise.";
            } else if (wordCount > 150) {
                lengthFeedback = "Your answer was quite detailed. While thoroughness is good, in an interview setting, try to be a bit more concise to respect the interviewer's time.";
            } else {
                lengthFeedback = "Your answer was well-paced and an appropriate length for an interview response.";
            }
            
            // Content-based feedback based on question type
            let contentFeedback = '';
            
            switch (questionType) {
                case 'behavioral':
                    if (!containsAny(answer.toLowerCase(), ['situation', 'task', 'action', 'result', 'problem', 'solution', 'outcome', 'learned'])) {
                        contentFeedback = "When answering behavioral questions, try using the STAR method: describe the Situation, Task, your Action, and the Result. This structure helps provide a complete and compelling story.";
                    } else {
                        contentFeedback = "Good use of storytelling elements in your response. Behavioral questions are best answered with specific examples, as you've done.";
                    }
                    break;
                    
                case 'technical':
                    if (!containsAny(answer.toLowerCase(), ['experience', 'approach', 'method', 'process', 'technique', 'technology', 'solution'])) {
                        contentFeedback = "For technical questions, focus on demonstrating your expertise by describing your approach, methodologies, and specific technologies you've used.";
                    } else {
                        contentFeedback = "Good technical response. You've shown your knowledge and practical experience effectively.";
                    }
                    break;
                    
                case 'personal':
                    if (!containsAny(answer.toLowerCase(), ['i believe', 'i think', 'my approach', 'personally', 'my experience', 'i feel'])) {
                        contentFeedback = "When answering personal questions, make sure to express your own perspective and highlight what makes you unique as a candidate.";
                    } else {
                        contentFeedback = "Good personal insight in your answer. You've effectively communicated your individual perspective.";
                    }
                    break;
                    
                case 'situational':
                    if (!containsAny(answer.toLowerCase(), ['would', 'could', 'might', 'approach', 'handle', 'manage', 'steps', 'first'])) {
                        contentFeedback = "For situational questions, outline the specific steps you would take to address the scenario, focusing on your problem-solving process.";
                    } else {
                        contentFeedback = "Good approach to the hypothetical situation. You've demonstrated your problem-solving abilities well.";
                    }
                    break;
                    
                case 'curveball':
                    contentFeedback = "Interesting response to an unexpected question. These questions often test your ability to think on your feet and show your personality. Your answer gives the interviewer insight into how you approach unusual challenges.";
                    break;
            }
            
            return `${lengthFeedback} ${contentFeedback}`;
        },

        generateOverallFeedback() {
            let feedback = "Based on our practice interview, here's my overall feedback:\n\n";
            
            // Personalize if we have the name
            if (this.context.userInfo.name) {
                feedback = `${this.context.userInfo.name}, based on our practice interview, here's my overall feedback:\n\n`;
            }
            
            // Add strengths section
            feedback += "Strengths:\n";
            feedback += "- You engaged well with the questions and provided thoughtful responses\n";
            
            // Determine what question types they handled well
            if (this.context.topicsFocused.has('behavioral')) {
                feedback += "- You showed good ability to provide specific examples from past experiences\n";
            }
            if (this.context.topicsFocused.has('technical')) {
                feedback += "- You effectively communicated your technical knowledge\n";
            }
            if (this.context.topicsFocused.has('situational')) {
                feedback += "- Your problem-solving approach to hypothetical scenarios was systematic\n";
            }
            
            // Add areas for improvement
            feedback += "\nAreas for improvement:\n";
            feedback += "- Continue practicing the STAR method for behavioral questions\n";
            feedback += "- Work on being concise while still providing enough detail\n";
            
            // Final encouragement
            feedback += "\nKeep practicing, and you'll become more confident and polished in your interview responses. Would you like to practice any specific types of questions further?";
            
            return feedback;
        },

        generateGenericResponse(input) {
            const lowerInput = input.toLowerCase();
            
            // Check for common interview questions or topics
            if (containsAny(lowerInput, ['hello', 'hi', 'hey', 'greetings'])) {
                return "Hello! I'm your AI interview assistant. How can I help you prepare for your interview today?";
            } 
            else if (containsAny(lowerInput, ['who are you', 'what can you do', 'how can you help'])) {
                return "I'm an AI interview assistant designed to help you prepare for job interviews. I can simulate interview questions, provide feedback on your answers, offer tips on body language, and help you understand what employers are looking for. What specific aspect of interview preparation would you like help with?";
            }
            else if (containsAny(lowerInput, ['ai interview', 'ai interviewer', 'automated interview'])) {
                return "AI-powered interviews are becoming increasingly common in the hiring process. These systems analyze your responses, facial expressions, tone, and word choice. To perform well, speak clearly, maintain eye contact with the camera, organize your thoughts, and use the STAR method (Situation, Task, Action, Result) for behavioral questions. Would you like to practice with some common AI interview questions?";
            }
            else if (containsAny(lowerInput, ['tips', 'advice', 'suggestions', 'help'])) {
                return "Here are some key interview tips: 1) Research the company thoroughly, 2) Practice your responses to common questions, 3) Prepare examples that highlight your skills and achievements, 4) Maintain good eye contact, 5) Pay attention to your body language, 6) Ask thoughtful questions about the role and company, and 7) Follow up with a thank-you note after the interview. Would you like more specific advice on any of these areas?";
            }
            else if (containsAny(lowerInput, ['common question', 'typical question', 'usually ask'])) {
                return "Common interview questions include: 'Tell me about yourself', 'Why do you want this job?', 'What are your strengths and weaknesses?', 'Where do you see yourself in 5 years?', 'Tell me about a challenge you faced and how you overcame it', and 'Why should we hire you?'. Would you like to practice answering any of these?";
            }
            else if (containsAny(lowerInput, ['tell me about yourself', 'introduce yourself'])) {
                return "This is often the first question in an interview. Focus on your professional background, relevant skills, and what makes you a good fit for the role. Keep it concise (1-2 minutes) and avoid personal details unless they're relevant to the job. Start with your current role, mention key achievements, then explain why you're interested in this position. Would you like to practice your response?";
            }
            else if (containsAny(lowerInput, ['strength', 'good at', 'excel'])) {
                return "When discussing strengths, be specific and provide examples. Choose strengths relevant to the role you're applying for. For example, instead of just saying 'I'm good at problem-solving,' say 'My problem-solving skills helped me increase efficiency by 20% in my last role by identifying and fixing bottlenecks in our workflow.' Back up your strengths with concrete achievements.";
            }
            else if (containsAny(lowerInput, ['weakness', 'improvement', 'develop'])) {
                return "When discussing weaknesses, be honest but strategic. Choose something that isn't critical to the job, and most importantly, explain how you're working to improve. For example: 'I sometimes get caught up in details. I've learned to set time limits for tasks and focus on higher-priority items first.' This shows self-awareness and a commitment to growth.";
            }
            else if (containsAny(lowerInput, ['body language', 'posture', 'eye contact'])) {
                return "Body language is crucial in interviews. Maintain good posture, make appropriate eye contact (look at the camera in virtual interviews), use natural hand gestures, and smile genuinely. Avoid crossing your arms (appears defensive), touching your face (shows nervousness), or fidgeting. Practice these habits beforehand so they feel natural during the actual interview.";
            }
            else if (containsAny(lowerInput, ['salary', 'compensation', 'pay', 'money'])) {
                return "When discussing salary, it's best to be prepared with market research for similar positions in your area. If asked about expectations, you can provide a range based on your research, or ask about their budget for the role. Wait until later in the interview process if possible, as this gives you more leverage once they're interested in hiring you.";
            }
            else if (containsAny(lowerInput, ['thank', 'appreciate', 'helpful'])) {
                return "You're welcome! I'm glad I could help. Is there anything else you'd like to know about interviewing or any other aspect of the job search process you'd like to discuss?";
            }
            else if (containsAny(lowerInput, ['bye', 'goodbye', 'see you', 'farewell'])) {
                return "Good luck with your interview preparation! Remember to stay confident and be yourself. Feel free to return anytime you need more practice or advice. You've got this!";
            }
            else {
                // Default response for inputs that don't match specific patterns
                return "That's an interesting point about the interview process. Would you like to simulate a full interview with me to practice your skills, or would you prefer specific advice about a particular aspect of interviewing?";
            }
        },

        getWelcomeMessage() {
            return "👋 Hello! I'm your AI interview assistant. I can help you prepare for your interview by simulating realistic interview questions and providing personalized feedback. Would you like to start a practice interview or ask questions about interview preparation?";
        }
    };

    // Welcome message when the page loads
    setTimeout(() => {
        addMessageToChat('ai', InterviewAI.init());
    }, 1000);

    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = chatInput.value.trim();
        if (message) {
            sendMessage(message);
            chatInput.value = '';
        }
    });

    // Handle "Clear" button click
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            fetch('/clear-chat-history', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    messagesContainer.innerHTML = '';
                    // Reset AI and re-add welcome message
                    setTimeout(() => {
                        addMessageToChat('ai', InterviewAI.init());
                    }, 500);
                }
            })
            .catch(error => console.error('Error:', error));
        });
    }

    function sendMessage(message) {
        // Add user message to chat
        addMessageToChat('user', message);

        // Show typing indicator
        showTypingIndicator();

        // Check if we should use server-side LLM or simulate locally
        if (shouldUseServerLLM(message)) {
            // Send message to server
            fetch('{{ url_for("start_interview") }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: 'message=' + encodeURIComponent(message)
            })
            .then(response => response.json())
            .then(data => {
                // Remove typing indicator
                removeTypingIndicator();
                // Add AI response to chat
                addMessageToChat('ai', data.response);
            })
            .catch(error => {
                console.error('Error:', error);
                removeTypingIndicator();
                simulateResponse(message);
            });
        } else {
            // Simulate response locally with a delay
            setTimeout(() => {
                removeTypingIndicator();
                simulateResponse(message);
            }, calculateResponseTime(message));
        }
    }

    function addMessageToChat(sender, message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.textContent = message;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message ai typing-indicator';
        typingDiv.id = 'typing-indicator';
        
        const dot1 = document.createElement('span');
        const dot2 = document.createElement('span');
        const dot3 = document.createElement('span');
        
        dot1.className = 'typing-dot';
        dot2.className = 'typing-dot';
        dot3.className = 'typing-dot';
        
        typingDiv.appendChild(dot1);
        typingDiv.appendChild(dot2);
        typingDiv.appendChild(dot3);
        
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    function calculateResponseTime(message) {
        // Calculate response time based on message complexity
        const baseTime = 1000; // Base time in milliseconds
        const charsPerSecond = 20; // Characters per second for "typing"
        
        // Get response first to calculate its length
        const response = InterviewAI.processInput(message);
        const responseLength = response.length;
        
        // Calculate time based on response length
        return Math.min(baseTime + (responseLength / charsPerSecond) * 1000, 5000);
    }

    function shouldUseServerLLM(message) {
        // Logic to determine if we should use server-side LLM
        // For this simulation, we'll use local responses
        return false;
    }

    function simulateResponse(message) {
        const response = InterviewAI.processInput(message);
        addMessageToChat('ai', response);
    }

    // Helper function to check if message contains any of the keywords
    function containsAny(text, keywords) {
        return keywords.some(keyword => text.includes(keyword));
    }

    // Add CSS styles for typing indicator
    const style = document.createElement('style');
    style.textContent = `
        .typing-indicator {
            display: flex;
            align-items: center;
            padding: 10px 15px;
        }
        
        .typing-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--text-secondary);
            margin: 0 3px;
            opacity: 0.6;
            animation: typing-dot 1.4s infinite ease-in-out;
        }
        
        .typing-dot:nth-child(1) {
            animation-delay: 0s;
        }
        
        .typing-dot:nth-child(2) {
            animation-delay: 0.2s;
        }
        
        .typing-dot:nth-child(3) {
            animation-delay: 0.4s;
        }
        
        @keyframes typing-dot {
            0%, 60%, 100% {
                transform: translateY(0);
            }
            30% {
                transform: translateY(-5px);
            }
        }
    `;
    document.head.appendChild(style);
}); 