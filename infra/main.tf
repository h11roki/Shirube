terraform {
  required_version = "~> 1.17.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "ap-southeast-2"
}

import {
  to = aws_key_pair.server
  id = "shirube"
}

import {
  to = aws_security_group.server
  id = "sg-0fd65d057894a5a33"
}

import {
  to = aws_instance.server
  id = "i-0f019c3fa2e397487"
}

import {
  to = aws_eip.server
  id = "eipalloc-04fdbd4a8055e2ead"
}

resource "aws_key_pair" "server" {
  key_name   = "shirube"
  public_key = trimspace(file("${path.module}/shirube.pub"))

  lifecycle {
    ignore_changes  = [public_key]
    prevent_destroy = true
  }
}

resource "aws_security_group" "server" {
  name        = "launch-wizard-1"
  description = "launch-wizard-1 created 2026-10-30T16:33:58.505Z"
  vpc_id      = "vpc-0a756800e8e4ff052"

  ingress {
    protocol    = "tcp"
    from_port   = 80
    to_port     = 80
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role" "server" {
  name = "shirube-server"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role_policy_attachment" "server_ssm" {
  role       = aws_iam_role.server.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_instance_profile" "server" {
  name = "shirube-server"
  role = aws_iam_role.server.name

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_instance" "server" {
  ami                    = "ami-0be7d1b5b9749d43a"
  instance_type          = "t4g.small"
  subnet_id              = "subnet-0093229e282dfee29"
  vpc_security_group_ids = [aws_security_group.server.id]
  key_name               = aws_key_pair.server.key_name
  iam_instance_profile   = aws_iam_instance_profile.server.name

  credit_specification {
    cpu_credits = "unlimited"
  }

  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = false
  }

  tags = {
    Name = "Shirube"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_eip" "server" {
  domain   = "vpc"
  instance = aws_instance.server.id

  lifecycle {
    prevent_destroy = true
  }
}

output "instance_id" {
  value = aws_instance.server.id
}

output "public_ip" {
  value = aws_eip.server.public_ip
}
