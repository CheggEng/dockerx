#!/usr/bin/env python

from build_utils import *


# Push the image to the Docker Hub
@docker
def push(params, context):
    image_name = context["image-name"]
    if image_name == None or image_name == "":
        if "tagged-image-name" in context:
            image_name = context["tagged-image-name"]
        if image_name == None or image_name == "":
            raise ValueError("Cannot push image without name!")

    log("Pushing image {0}".format(image_name))
    dockerRead('docker push {0}'.format(image_name), connect=docker_connect)


# Tag the image.
# Parameters format - [image-name][:tag]
@docker
def tag(params, context):
    image_id = context["image-id"]
    image_name = context["image-name"]
    parsed_params = params.split(':', 1)
    new_image_name = None
    new_image_tag = None
    if len(parsed_params) > 1:
        if parsed_params[0] != '':
            new_image_name = parsed_params[0]
        new_image_tag = parsed_params[1]
    else:
        new_image_name = parsed_params[0]
    if new_image_name == None:
        if image_name == None:
            raise ValueError("Image name is not set!")
        else:
            image_name = image_name.split(':', 1)[0]
    else:
        image_name = new_image_name
    if new_image_tag == None:
        if image_name != None and len(image_name.split(':', 1)) > 1:
            image_tag = image_name.split(':', 1)[1]
        else:
            image_tag = "latest"
    else:
        image_tag = new_image_tag
    log('Tagging image with id {image_id} as {image_name}:{image_tag}'.format(image_id=image_id, image_name=image_name,
                                                                              image_tag=image_tag))
    dockerRead('docker tag {image_id} {image_name}:{image_tag}'.format(image_id=image_id, image_name=image_name,
                                                                       image_tag=image_tag), connect=docker_connect)
    context["tagged-image-name"] = image_name + ":" + image_tag
