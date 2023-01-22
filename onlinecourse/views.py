from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Lesson, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# <HINT> Create a submit view to create an exam submission record for a course enrollment,
# you may implement it based on following logic:
         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
         # Create a submission object referring to the enrollment
         # Collect the selected choices from exam form
         # Add each selected choice object to the submission object
         # Redirect to show_exam_result with the submission id
def submit(request, course_id, lesson_id):
    # Lesson id retrieved from the exam form
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    
    enrollment = Enrollment.objects.get(user=user, course=course)
    submission = Submission.objects.create(enrollment=enrollment)
    submission_id = submission.id

    total_choices = extract_answers(request)
    submission.choices.set(total_choices)

    # Passing the lesson id retrieved from the exam form
    # This makes the selection of lesson independent of any choices made
    return HttpResponseRedirect(reverse(viewname="onlinecourse:exam_result", args=(course_id, lesson_id, submission_id)))
    

# <HINT> A example method to collect the selected choices from the exam form from the request object
def extract_answers(request):
   submitted_anwsers = []
   for key in request.POST:
       if key.startswith('choice'):
           value = request.POST[key]
           choice_id = int(value)
           submitted_anwsers.append(choice_id)
   return submitted_anwsers


# <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
# you may implement it based on the following logic:
        # Get course and submission based on their ids
        # Get the selected choice ids from the submission record
        # For each selected choice, check if it is a correct answer or not
        # Calculate the total score
        
def show_exam_result(request, course_id, lesson_id, submission_id):
    # This lesson id is eventually used to retrieve the concerened lesson
    context = {}
    # Get course
    course = get_object_or_404(Course, pk=course_id)
    # Get Lesson
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    # Get question set for the above lesson
    question_set = Question.objects.filter(lesson=lesson)
    # Get submission object
    submission = Submission.objects.get(id=submission_id)
    # Retrieve the choice set of the submission
    choice_set = submission.choices.all()
    # Get the total question count related to the concerened lesson
    count = question_set.count()

    # Retrieve question ids in choice set - 
    # Required to evaluate multiple choice questions and unattempted questions
    question_ids = [] 
    score = 0
    total_score = 0

    for choice in choice_set:
        question_ids.append(choice.question.id)

    question_ids = [*set(question_ids)]

    for q in question_ids:
        curr_ques = Question.objects.get(id = q)
        choices = choice_set.filter(question=curr_ques)
        if curr_ques.is_get_score(choices):
            score += curr_ques.mark
    
    total_score = round((score/count)*100, 2)

    # Pass the context with the concerened lesson along with other parameters - 
    # This helps in displaying the content related to the lesson only
    context = {
        "course" : course,
        "lesson" : lesson,
        "grade" : total_score,
        "choices" : choice_set
    }

    return render(request, 'onlinecourse/exam_result_bootstrap.html', context) 