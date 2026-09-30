pipeline {
    agent any

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Validate') {
            steps {
                sh '''
                    test -f Dockerfile
                    test -f index.html
                    test -f k8s/deployment.yaml
                    test -f k8s/service.yaml
                    echo "Required files are present"
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    docker build -t nginx-demo:${BUILD_NUMBER} .
                '''
            }
        }

        stage('Container Test') {
            steps {
                sh '''
                    docker run -d \
                      --name nginx-demo-test-${BUILD_NUMBER} \
                      -p 8085:80 \
                      nginx-demo:${BUILD_NUMBER}

                    sleep 3

                    curl -f http://localhost:8085

                    docker rm -f nginx-demo-test-${BUILD_NUMBER}
                '''
            }
        }
    }

    post {
        always {
            sh '''
                docker rm -f nginx-demo-test-${BUILD_NUMBER} 2>/dev/null || true
            '''
        }

        success {
            echo 'CI pipeline completed successfully.'
        }

        failure {
            echo 'CI pipeline failed.'
        }
    }
}
