from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.template import loader

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from django.template.defaultfilters import slugify

from web_app.models import *
from web_app.forms import *

#Display the home page
def index(request):
    #List every profession in database
    professions_list = Profession.objects.all()
    context_dict={}
    context_dict['professions']= professions_list
    return render(request, 'web_app/index.html', context_dict)

#Display the professions page
def profession(request, profession_name_slug):
    context_dict = {}

    try:
        #Get the profession that matches the profession in the URL
        #Get the tags and posts related to this profession
        profession = Profession.objects.get(slug=profession_name_slug)
        tags = Tags.objects.filter(profession=profession)

    except Profession.DoesNotExist:
        #If the url does not have an existing profession show an error page
        context_dict['item'] = ''.join(('Profession, ', profession_name_slug, ','))
        return render(request, 'web_app/missing_content.html', context_dict)

    context_dict['tags'] = tags
    context_dict['profession'] = profession

    return render(request, 'web_app/profession.html', context_dict)

#Load in the filtered professions
def profession_filter(request):
    context_dict={}
    if request.method == 'POST':
        
        profession_name_slug=request.POST.get('slug')
        profession = Profession.objects.get(slug=profession_name_slug)
        
        checkboxes = request.POST.getlist('checkboxes[]')
        tags = Tags.objects.filter(profession=profession)

        #tag filter is a list of tags the user wants to include
        tag_filter = []

        #loop through each tag and its corresponding checkbox
        for tag, checkbox in zip(tags, checkboxes):
            #check if the corresponding tag has been ticked in the html form
            if checkbox == 'true': #see if the checkbox was ticked
                #if ticked, create a post tags object to say they included this tag
                tag_filter.append(tag)

        #Get all posts in this profession
        #Get all post-tag relations that match the filtered subset of tags
        #Filter the posts that only appear with these tags
        posts = Posts.objects.filter(profession=profession).order_by('-pid') #order by most recently posted first
        tags = PostTags.objects.filter(tag__in=tag_filter).values('post_id')
        posts = posts.filter(pid__in=tags)

        posts_likes = {}
        for post in posts:
            posts_likes[post]=len(PostLikes.objects.filter(post=post))
        
        #store relevant tags and professions
        context_dict['tags'] = tags
        context_dict['profession'] = profession
        context_dict['posts'] = posts_likes
        #number of posts with these tags in this profession
        context_dict['count'] = len(posts)

        return render(request, 'web_app/profession_posts.html', context_dict)

    
#Display the Profile Page
def profile(request, user_name_slug):
    context_dict = {}
    try:
        #Get the user that matches the user slug in the URL
        user = UserProfile.objects.get(slug=user_name_slug)
        context_dict['profile'] = user

        #if user is available, add the "Available" message and their email
        if user.available:
            context_dict['available'] = "Available"
            context_dict['email'] = user.user.email
        else:
            context_dict['available'] = "Not Available"
            context_dict['email'] = ''
        
        #add the users external links e.g instagram or facebook
        links = UserLinks.objects.filter(user=user.user)
        context_dict['links'] = {} 
        #dictionary of key: site name, and value: URL
        for link in links:
            context_dict['links'][link.site_name] = link.link

        #Add the sections and posts within the sections owned by the user
        sections = Section.objects.filter(user=user.user)
        context_dict['sections'] = {}

        for section in sections:
            posts = Posts.objects.filter(section = section)
            context_dict['sections'][section.name]={}
            for post in posts:
                #create a dictionary containing the post and number of likes
                context_dict['sections'][section.name][post]=len(PostLikes.objects.filter(post=post))

        #Boolean to check if the user is viewing their own page
        context_dict['owner'] = (user.user == request.user)
        #Boolean to check if the user has reached maximum of 5 links. If less than
        #5 then they add link option will be available
        context_dict['5links'] = (len(UserLinks.objects.filter(user=user.user))<5)

        return render(request, 'web_app/profile.html', context_dict)

    #If the URL contains a user name that does not exist show error page
    except UserProfile.DoesNotExist:
        context_dict['item'] = ''.join(('User, ', user_name_slug, ','))
        return render(request, 'web_app/missing_content.html', context_dict)


#VIEW A POST AND ALL IT'S DETAILS 
def post(request, posts_pid):
    context_dict={}
    try:
        #Find the post with the matching ID in the URL
        post = Posts.objects.get(pid=posts_pid)
        context_dict['post'] = post
    #If the URL containing the post ID does not exist, show error page
    except Posts.DoesNotExist:
        context_dict['item'] = ''.join(('Post with ID: ', posts_pid, ','))
        return render(request, 'web_app/missing_content.html', context_dict)

    #Get the tags of this post
    tags = PostTags.objects.filter(post=post)
    context_dict['tags']=tags 

    context_dict['likes'] = len(PostLikes.objects.filter(post=post))

    #Find the creater of the post. Section has attribute user, post has attribute section
    user = post.section.user
    profile = UserProfile.objects.get(user=user)
    context_dict['profile']=profile

    #LIKE/UNLIKE BUTTON
    #check user is logged in
    if request.user.is_authenticated:
        #has user liked post?
        try:
            like = PostLikes.objects.get(post=post, user=request.user)
            liked= True
        except:
            liked= False

        #if they have liked it, button should present option to 'unlike' it
        context_dict['liked'] = liked
        
        if request.method == 'POST':
            if liked:
                like.delete()
            else:
                PostLikes.objects.get_or_create(user=request.user, post=post)
        
    return render(request, 'web_app/post.html', context_dict)


def get_server_side_cookie(request, cookie, default_val=None):
    val = request.session.get(cookie)
    if not val:
        val = default_val
    return val


#ADD A POST TO A SECTION IN THE USERS PROFILE
@login_required
def add_post(request):   

    context={}
    #Form for general post attributes.     
    post_form = CreatePostForm(user=request.user)
    
    #get each tag that matches the users profession
    tag_list = Tags.objects.filter(profession=request.user.userprofile.profession)

    if request.method == 'POST':

        post_form = CreatePostForm(request.POST, request.FILES, user=request.user)

        # Have we been provided with a valid form?
        if post_form.is_valid():

            #SAVE POST FORM
            post = post_form.save(commit=False)
            #set the profession to that of the user
            post.profession = UserProfile.objects.get(user=request.user).profession
            #save picture to appropriate location
            if 'picture' in request.FILES:
                post.picture = request.FILES['picture']
            #save to database
            post.save()

            #loop through each tag
            for tag in tag_list:
                #check if the corresponding tag has been ticked in the html form
                check = request.POST.get(tag.name)
                if check !=None: #see if the checkbox was ticked
                    #if ticked, create a post tags object to say they included this tag
                    post_tag = PostTags.objects.create(tag=tag, post=post)
                    post_tag.save()

            #identify the post to redirect to correct post URL
            posts_pid=post.pid
            return redirect(reverse('design-grid:post', kwargs={'posts_pid': posts_pid} ))
        else:
            # The supplied form contained errors -
            context['alert'] = "Error whilst processing your request"
    
    context['post_form']=post_form
    context['tags']=tag_list
    # Will handle the bad form, new form, or no form supplied cases.
    # Render the form with error messages (if any).
    return render(request, 'web_app/add_post.html', context=context)


#ADD A SECTION (WHICH CONTAINS POSTS) TO THE USERS PROFILE
@login_required
def add_section(request):
    
    if request.method == 'POST':

        form = CreateSectionForm(request.POST)
    
        # Have we been provided with a valid form?
        if form.is_valid():
            #Save the form but not to database
            #set the user of the section to the current user
            #save to database
            section = form.save(commit=False)
            section.user = request.user
            section.save()
            
            #Redirect to the users profile page
            user_name_slug = UserProfile.objects.get(user=request.user).slug
            return redirect(reverse('design-grid:profile', kwargs={'user_name_slug': user_name_slug } ))
        else:
            # The supplied form contained errors -
            return render(request, 'web_app/add_link.html', context={'alert':'Do you already have a section with this name?','form': form})

    else:
        form = CreateSectionForm()
        # Will handle the bad form, new form, or no form supplied cases.
        # Render the form with error messages (if any).
        return render(request, 'web_app/add_section.html', {'form': form})


#MODIFY THE USERS PROFILE
@login_required
def edit_profile(request):
    saved = False #If saved, template will offer URL to move to profile page

    context={}
    if request.method == 'POST':
        #Pass the user profile as an instance.
        #This informs the form what profile to edit
        user_profile = UserProfile.objects.get(user=request.user)
        profile_form = EditProfileForm(request.POST, instance=user_profile)

        if profile_form.is_valid():

            profile = profile_form.save(commit=False)
            profile.user = request.user

            #Store the picture in MEDIA files
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']
            
            profile.save()
            
            #Inform the user in the template that the process is complete
            #Template will offer URL to move to profile page
            saved = True
        else:
            #Will produce errors if the form is not completed correctly
            context['alert'] = "Invalid details supplied."
    else:
        #Base form
        user_profile = UserProfile.objects.get(user=request.user)
        profile_form = EditProfileForm(instance=user_profile)

    context['profile_form']= profile_form
    context['saved']= saved
    #Render the page
    return render(request, 'web_app/edit_profile.html', context=context)


#ADD A LINK TO THE USERS PROFILE
@login_required
def add_link(request):
    if request.method == 'POST':

        form = UserLinksForm(request.POST)
    
        # Have we been provided with a valid form?
        if form.is_valid():
            #Save the form but not to database
            #set the user of the section to the current user
            #save to database
            link = form.save(commit=False)
            link.user = request.user
            link.save()
            
            #Redirect to the users profile page
            user_name_slug = UserProfile.objects.get(user=request.user).slug
            return redirect(reverse('design-grid:profile', kwargs={'user_name_slug': user_name_slug } ))
        else:
            # The supplied form contained errors -
            return render(request, 'web_app/add_link.html', context={'alert':' Someone has already claimed this URL.','form': form})

    else:
        form = UserLinksForm()
        # Will handle the bad form, new form, or no form supplied cases.
        # Render the form with error messages (if any).
        return render(request, 'web_app/add_link.html', {'form': form})


#DISPLAY RESULTS OF SEARCH
def search(request, argument):
    context_dict={}
    
    context_dict['argument'] = argument
    #list users with matching name
    users = User.objects.filter(username__icontains=argument)
    context_dict['users']= users
    #list users with matching location
    profile = UserProfile.objects.filter(location__icontains=argument)
    context_dict['location']= profile
    #list post with matching titles
    posts = Posts.objects.filter(title__icontains=argument)
    context_dict['posts']= posts

    
    #TEMPORARY WILL READ FROM SEARCH BAR IN BASE.HTML LATER
    if request.method == 'POST':
        search = request.POST.get('search') #read in input of search bar

        if search: #if there is an input
            #look up the search term
            return redirect(reverse('design-grid:search', kwargs={'argument': search } ))
    
    # The request is not a HTTP POST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    return render(request, 'web_app/search.html', context_dict)


#REGISTER A NEW USER
def register(request):

    #if user is logged in, redirect them to home page
    if request.user.is_authenticated:
        return redirect(reverse('design-grid:index'))

    registered = False

    if request.method == 'POST':

        user_form = UserForm(request.POST)
        profile_form = UserProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():

            user = user_form.save()
            user.set_password(user.password)
            user.save()

            #include profession and link user to user profile
            profile = profile_form.save(commit=False)
            profile.user = user

            profile.save()
            registered = True
        else:
            print(user_form.errors, profile_form.errors)
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    return render(request, 'web_app/register.html', context={'user_form': user_form, 'profile_form': profile_form,
                                                           'registered': registered})


#LOG IN AS AN EXISTING USER
def user_login(request):

    #if user is logged in, redirect them to home page
    if request.user.is_authenticated:
        return redirect(reverse('design-grid:index'))

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)

        if user:
            # Is the account active? It could have been disabled.
            if user.is_active:
                login(request, user)

                #if the user is a super user, they will not have a profile to redirect to
                if request.user.is_superuser:
                    return redirect(reverse('design-grid:index'))

                user_name_slug = UserProfile.objects.get(user=user).slug
                return redirect(reverse('design-grid:profile', kwargs={'user_name_slug': user_name_slug } ))
            else:
                # An inactive account was used - no logging in
                return render(request, 'web_app/login.html', context={'alert':'Your account has been disabled'})
        else:
            # Bad login details were provided. So we can't log the user in.
            return render(request, 'web_app/login.html', context={'alert':'Email or password is incorrect'})
    
    # The request is not a HTTP POST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    else:
        return render(request, 'web_app/login.html')


#LOG OUT AND REDIRECT TO HOME PAGE
@login_required
def user_logout(request):
    logout(request)
    return redirect(reverse('design-grid:index'))



def handler404(request, exception):
    return render(request, 'web_app/errors.html', status=404, context={"error_num":"404","error_msg":"PAGE NOT FOUND."})

def handler403(request, exception):
    return render(request, 'web_app/errors.html', status=403, context={"error_num":"403","error_msg":"FORBIDDEN."})

def handler500(request):
    return render(request, 'web_app/errors.html', status=500, context={"error_num":"500","error_msg":"SERVER ERROR."})